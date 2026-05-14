import httpx
from app.models.apiParser import (
    Project,
    SwaggerDocument,
    API,
    APIParameter,
    APIResponse,
    APIDependency,
    APIAuth,
    ParameterMapping
)
from app.services.aiServices import infer_dependencies_with_llm
from app.agents.apiParserAgent import executeAPIParserAgent

class APIParserService:
    def __init__(self, db_session):
        self.enable_llm = True  # Toggle LLM-based inference
        self.db = db_session


    async def create_project(self, project_details):
        try:
            new_project = Project(
                name=project_details.project_name,
                description=project_details.project_description
            )
            self.db.add(new_project)
            await self.db.commit()
            await self.db.refresh(new_project)
            return new_project.id
        except Exception as e:
            await self.db.rollback()
            raise Exception("Error creating project: " + str(e))

    async def get_project(self, project_id):
        try:
            project = await self.db.get(Project, project_id)
            if not project:
                raise Exception("Project not found")
            return {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "created_at": project.created_at
            }
        except Exception as e:
            raise Exception("Error fetching project: " + str(e))
        
    async def fetch_swagger(self, swagger_url: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(swagger_url)
                response.raise_for_status()
        except httpx.RequestError as e:
            raise ValueError(f"Failed to connect: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise ValueError(f"HTTP error: {e.response.status_code}")

        try:
            return response.json()
        except Exception:
            raise ValueError("Invalid JSON response (not a Swagger doc)")
        
    async def executeAgent(self, swaggerJson: dict, projectId: str):
        try:
            swaggerId = await self.parse_swagger(swaggerJson, projectId)
            # await executeAPIParserAgent(swaggerId,self.db)
        except Exception as e:
            raise Exception("Error executing API Parser Agent: " + str(e))

    async def parse_swagger(self, swagger_json: dict, project_id: str):
        """
        Hybrid Swagger parser:
        - Rule-based extraction (deterministic)
        """

        # -------------------------------
        # 1. Validate Swagger
        # -------------------------------
        if not isinstance(swagger_json, dict):
            raise ValueError("Invalid swagger_json format")

        if "paths" not in swagger_json:
            raise ValueError("Invalid Swagger: 'paths' missing")

        version = swagger_json.get("openapi") or swagger_json.get("swagger")
        if not version:
            raise ValueError("Not a valid Swagger/OpenAPI document")

        # -------------------------------
        # 2. Store Swagger Document
        # -------------------------------
        swagger_id = None

        swagger_doc = SwaggerDocument(
            project_id=project_id,
            version=version, # get version from database. add +1 for increment
            raw_json=swagger_json
        )
        self.db.add(swagger_doc)
        await self.db.flush()

        # -------------------------------
        # 3. Authentication Handling
        # -------------------------------
        auth_schemes = self._extract_auth_schemes(swagger_json)
        print(f"Extracted Auth Schemes: {auth_schemes}")
        swagger_id = swagger_doc.id
        # -------------------------------
        # 4. Parse APIs
        # -------------------------------

        for path, methods in swagger_json["paths"].items():
            for method, details in methods.items():

                if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    continue
                api_key = f"{method.upper()}_{path}"

                api = API(
                    swagger_id=swagger_doc.id,
                    operation_id = details.get("operationId"),
                    unique_path= api_key,
                    path=path,
                    method=method.upper(),
                    summary=details.get("summary"),
                    description=details.get("description"),
                    tag=details.get("tags", [None])[0]
                )
                print(f"Parsing API: {method.upper()} {path}")
                self.db.add(api)
                await self.db.flush()

                # -------------------------------
                # Parameters
                # -------------------------------
                for param in details.get("parameters", []):
                    schema = param.get("schema", {})

                    param_name = param.get("name")

                    api_param = APIParameter(
                        api_id=api.id,
                        name=param_name,
                        location=param.get("in"),
                        required=param.get("required", False),
                        type =schema.get("type") or param.get("type"),
                        schema =param.get("schema")
                    )
                    print(f"  - Parameter: {param_name} (in: {param.get('in')}, type: {schema.get('type')})")
                    self.db.add(api_param)

                # -------------------------------
                # Request Body
                # -------------------------------
                request_body = self._extract_request_body(details, swagger_json)
                content = request_body.get("content", {})

                for content_type, schema_info in content.items():
                    schema = schema_info.get("schema", {})

                    # ref = schema.get("$ref")
                    # if ref:
                    #     schema_name = ref.split("/")[-1]

                    #     # OPTIONAL: resolve schema manually
                    #     resolved_schema = self._resolve_schema_refs(schema, swagger_json)
                    # else:
                    #     resolved_schema = schema
                    resolved_schema = self._resolve_schema_refs(schema, swagger_json)
                    api_param = APIParameter(
                        api_id=api.id,
                        name="body",
                        location="body",
                        required=request_body.get("required", False),
                        type=schema.get("type"),
                        schema =resolved_schema
                    )
                    print(f"  - Request Body: (content-type: {content_type}, type: {schema.get('type')})")
                    self.db.add(api_param)

                # -------------------------------
                # Responses
                # -------------------------------
                for status_code, response in details.get("responses", {}).items():

                    content_map = self._extract_response_content(response)

                    # Handle responses without schema/content
                    if not content_map:
                        api_response = APIResponse(
                            api_id=api.id,
                            status_code=status_code,
                            schema=None,
                            content_type=None,
                            description=response.get("description")
                        )
                        print(f"  - Response: {status_code} (no schema)")
                        self.db.add(api_response)
                        continue

                    for content_type, schema_info in content_map.items():
                        schema = schema_info.get("schema", {})

                        # -------------------------------
                        # Resolve $ref
                        # -------------------------------
                        # ref = schema.get("$ref")
                        # if ref:
                        #     schema_name = ref.split("/")[-1]
                        #     resolved_schema = self._resolve_schema_refs(schema, swagger_json)
                        # else:
                        #     resolved_schema = schema

                        resolved_schema = self._resolve_schema_refs(schema, swagger_json)

                        # -------------------------------
                        # Handle array schemas
                        # -------------------------------
                        if resolved_schema.get("type") == "array":
                            items = resolved_schema.get("items", {})
                            item_ref = items.get("$ref")

                            if item_ref:
                                schema_name = item_ref.split("/")[-1]
                                

                        # -------------------------------
                        # Extract nested refs
                        # -------------------------------
                        refs = self._extract_refs(resolved_schema)

                        # -------------------------------
                        # Store response
                        # -------------------------------
                        api_response = APIResponse(
                            api_id=api.id,
                            status_code=status_code,
                            schema=resolved_schema,
                            content_type=content_type,
                            description=response.get("description")
                        )
                        print(f"  - Response: {status_code} (content-type: {content_type})")
                        self.db.add(api_response)
                # -------------------------------
                # Auth Attach
                # -------------------------------
                self._attach_auth(api, details, swagger_json, auth_schemes)

        await self.db.commit()
        return swagger_id

    def _attach_auth(self, api, details, swagger_json, auth_schemes):
        """
        Attach correct auth to API
        """

        security = details.get("security", swagger_json.get("security", []))

        if not security:
            return

        for sec in security:
            for sec_name in sec.keys():
                scheme = auth_schemes.get(sec_name)

                # Skip if scheme not found
                if not scheme:
                    continue

                auth_type = scheme.get("type")

                # Skip invalid or incomplete auth
                if not auth_type:
                    continue

                config = {}

                # apiKey
                if auth_type == "apiKey":
                    if not scheme.get("name") or not scheme.get("in"):
                        continue

                    config = {
                        "in": scheme.get("in"),
                        "name": scheme.get("name"),
                    }

                # bearer token
                elif auth_type == "bearer":
                    config = {
                        "in": "header",
                        "name": "Authorization",
                        "scheme": "Bearer"
                    }

                # Skip oauth2 for MVP (incomplete handling)
                elif auth_type == "oauth2":
                    continue

                else:
                    continue

                api_auth = APIAuth(
                    api_id=api.id,
                    auth_type=auth_type,
                    config=config
                )

                self.db.add(api_auth)
                return
            
    def _extract_auth_schemes(self, swagger_json: dict):
        """
        Extract and normalize authentication schemes
        """

        auth_schemes = {}

        # OpenAPI 3
        security_schemes = swagger_json.get("components", {}).get("securitySchemes", {})

        # Swagger 2 fallback
        if not security_schemes:
            security_schemes = swagger_json.get("securityDefinitions", {})

        for name, scheme in security_schemes.items():
            scheme_type = scheme.get("type")

            # 🚨 Skip invalid schemes
            if not scheme_type:
                continue

            normalized = {
                "type": scheme_type,              # apiKey / http / oauth2
                "in": scheme.get("in"),
                "name": scheme.get("name"),
                "scheme": scheme.get("scheme"),
            }

            if scheme_type == "http" and scheme.get("scheme") == "bearer":
                normalized["type"] = "bearer"
                normalized["name"] = "Authorization"

            auth_schemes[name] = normalized

        return auth_schemes

    def _extract_request_body(self, details, swagger_json):
        """
        Supports both OpenAPI3 and Swagger2
        """
        # OpenAPI 3
        if "requestBody" in details:
            return details.get("requestBody", {})

        # Swagger 2 fallback
        for param in details.get("parameters", []):
            if param.get("in") == "body":
                return {
                    "required": param.get("required", False),
                    "content": {
                        "application/json": {
                            "schema": param.get("schema", {})
                        }
                    }
                }
        return {}
        
    def _resolve_schema_refs(self, obj, swagger_json, visited=None):
        """
        Recursively resolve ALL $ref occurrences
        inside Swagger/OpenAPI schemas.
        """

        if visited is None:
            visited = set()

        # -----------------------------------
        # Handle dict
        # -----------------------------------
        if isinstance(obj, dict):

            # -----------------------------------
            # Resolve direct $ref
            # -----------------------------------
            if "$ref" in obj:

                ref = obj["$ref"]

                # Prevent circular recursion
                if ref in visited:
                    return {"$ref": ref}

                visited.add(ref)

                # -----------------------------------
                # Resolve path safely
                # -----------------------------------
                parts = ref.strip("#/").split("/")

                resolved = swagger_json

                for part in parts:

                    if not isinstance(resolved, dict):
                        print(f"Invalid ref path: {ref}")
                        return obj

                    resolved = resolved.get(part)

                    if resolved is None:
                        print(f"Ref not found: {ref}")
                        return obj

                # -----------------------------------
                # Merge sibling fields
                # -----------------------------------
                merged = {
                    **resolved,
                    **{k: v for k, v in obj.items() if k != "$ref"}
                }

                return self._resolve_schema_refs(
                    merged,
                    swagger_json,
                    visited.copy()
                )

            # -----------------------------------
            # Resolve child keys recursively
            # -----------------------------------
            resolved_dict = {}

            for key, value in obj.items():
                resolved_dict[key] = self._resolve_schema_refs(
                    value,
                    swagger_json,
                    visited.copy()
                )

            return resolved_dict

        # -----------------------------------
        # Handle list
        # -----------------------------------
        elif isinstance(obj, list):

            return [
                self._resolve_schema_refs(
                    item,
                    swagger_json,
                    visited.copy()
                )
                for item in obj
            ]

        # -----------------------------------
        # Primitive values
        # -----------------------------------
        return obj
    
    def _extract_response_content(self, response):
        """
        Normalize Swagger2 and OpenAPI3 response formats
        """
        # OpenAPI 3
        if "content" in response:
            return response.get("content", {})

        # Swagger 2
        schema = response.get("schema")
        if schema:
            return {
                "application/json": {
                    "schema": schema
                }
            }

        return {}
    
    def _extract_refs(self, schema):
        """
        Recursively extract all $ref schema names from a schema
        """
        refs = []

        if isinstance(schema, dict):
            for key, value in schema.items():
                if key == "$ref" and isinstance(value, str):
                    # Extract schema name from ref
                    schema_name = value.split("/")[-1]
                    refs.append(schema_name)
                else:
                    refs.extend(self._extract_refs(value))

        elif isinstance(schema, list):
            for item in schema:
                refs.extend(self._extract_refs(item))

        return refs