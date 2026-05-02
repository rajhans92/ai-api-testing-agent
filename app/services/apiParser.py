from app.models.apiParser import (
    Project,
    SwaggerDocument,
    API,
    APIParameter,
    APIResponse,
    APIDependency,
    APIAuth
)

class APIParserService:
    def __init__(self, db_session):
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
        
    async def parse_swagger(self, swagger_json: dict, project_id: str):
        """
        Hybrid Swagger parser:
        - Rule-based extraction (deterministic)
        - Dependency detection (schema + param level)
        - LLM hook for advanced inference
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
        swagger_doc = SwaggerDocument(
            project_id=project_id,
            version=version,
            raw_json=swagger_json
        )
        self.db.add(swagger_doc)
        self.db.flush()

        components = swagger_json.get("components", {})
        schemas = components.get("schemas", {})

        # -------------------------------
        # 3. Authentication Handling
        # -------------------------------
        auth_schemes = self._extract_auth_schemes(swagger_json)

        # -------------------------------
        # 4. Parse APIs
        # -------------------------------
        api_map = {}
        schema_producers = {}
        param_index = {}

        for path, methods in swagger_json["paths"].items():
            for method, details in methods.items():

                if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    continue

                api = API(
                    project_id=project_id,
                    swagger_id=swagger_doc.id,
                    operation_id = details.get("operationId"),
                    path=path,
                    method=method.upper(),
                    summary=details.get("summary"),
                    description=details.get("description"),
                    tag=details.get("tags", [None])[0]
                )
                self.db.add(api)
                self.db.flush()

                api_key = f"{method.upper()} {path}"

                api_map[api_key] = {
                    "api": api,
                    "details": details
                }

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
                    self.db.add(api_param)

                    # Index for dependency detection
                    param_index.setdefault(param_name.lower(), []).append(api.id)

                # -------------------------------
                # Request Body
                # -------------------------------
                request_body = self._extract_request_body(details, swagger_json)
                content = request_body.get("content", {})

                for content_type, schema_info in content.items():
                    schema = schema_info.get("schema", {})

                    ref = schema.get("$ref")
                    if ref:
                        schema_name = ref.split("/")[-1]

                        # Track dependency
                        param_index.setdefault(schema_name.lower(), []).append(api.id)
                        # OPTIONAL: resolve schema manually
                        resolved_schema = self._resolve_schema_ref(ref, swagger_json)
                    else:
                        resolved_schema = schema

                    api_param = APIParameter(
                        api_id=api.id,
                        name="body",
                        location="body",
                        required=request_body.get("required", False),
                        type=schema.get("type"),
                        schema =resolved_schema
                    )
                    self.db.add(api_param)

                # -------------------------------
                # Responses
                # -------------------------------
                for status_code, response in details.get("responses", {}).items():

                    content_map = self._extract_response_content(response)

                    for content_type, schema_info in content_map.items():
                        schema = schema_info.get("schema", {})

                        # -------------------------------
                        # Resolve $ref (if needed)
                        # -------------------------------
                        ref = schema.get("$ref")
                        if ref:
                            schema_name = ref.split("/")[-1]
                            resolved_schema = self._resolve_schema_ref(ref, swagger_json)

                            # Mark as producer
                            schema_producers.setdefault(schema_name, []).append(api.id)
                        else:
                            resolved_schema = schema

                        # -------------------------------
                        # Handle array schemas
                        # -------------------------------
                        if resolved_schema.get("type") == "array":
                            items = resolved_schema.get("items", {})
                            item_ref = items.get("$ref")

                            if item_ref:
                                schema_name = item_ref.split("/")[-1]
                                schema_producers.setdefault(schema_name, []).append(api.id)

                        # -------------------------------
                        # Extract nested refs (IMPORTANT)
                        # -------------------------------
                        refs = self._extract_refs(resolved_schema)
                        for ref_name in refs:
                            schema_producers.setdefault(ref_name, []).append(api.id)

                        # -------------------------------
                        # Store FULL response
                        # -------------------------------
                        api_response = APIResponse(
                            api_id=api.id,
                            status_code=status_code,
                            description=response.get("description"),
                            schema=resolved_schema,
                            content_type=content_type
                        )

                        self.db.add(api_response)
                # -------------------------------
                # Auth Attach
                # -------------------------------
                self._attach_auth(api, details, swagger_json, auth_schemes)

        # -------------------------------
        # 5. Rule-Based Dependency Detection
        # -------------------------------

        dependencies = []

        # Schema-based dependency
        for schema_name, producers in schema_producers.items():
            consumers = param_index.get(schema_name.lower(), [])

            for consumer_api in consumers:
                for producer_api in producers:
                    if consumer_api != producer_api:
                        dependencies.append({
                            "api_id": consumer_api,
                            "depends_on_api_id": producer_api,
                            "type": "schema"
                        })

        # Param-name based dependency (weak but useful)
        for param_name, api_ids in param_index.items():
            if len(api_ids) > 1:
                for consumer in api_ids:
                    for producer in api_ids:
                        if consumer != producer:
                            dependencies.append({
                                "api_id": consumer,
                                "depends_on_api_id": producer,
                                "type": "param"
                            })

        # Save dependencies
        for dep in dependencies:
            self.db.add(APIDependency(
                api_id=dep["api_id"],
                depends_on_api_id=dep["depends_on_api_id"],
                dependency_type=dep["type"]
            ))

        # -------------------------------
        # 6. LLM-Based Dependency Enhancement (Optional)
        # -------------------------------
        if self.enable_llm:
            llm_dependencies = self._infer_dependencies_with_llm(api_map)

            for dep in llm_dependencies:
                self.db.add(APIDependency(
                    api_id=dep["api_id"],
                    depends_on_api_id=dep["depends_on_api_id"],
                    dependency_type="llm"
                ))

        # -------------------------------
        # 7. Commit
        # -------------------------------
        self.db.commit()

    def _attach_auth(self, api, details, swagger_json, auth_schemes):
        security = details.get("security", swagger_json.get("security", []))

        if not security:
            return

        for sec in security:
            for sec_name in sec.keys():
                scheme = auth_schemes.get(sec_name)

                if not scheme:
                    continue

                api_auth = APIAuth(
                    api_id=api.id,
                    auth_type=scheme.get("type"),
                    config={
                        "scheme": scheme.get("scheme"),
                        "in": scheme.get("in"),
                        "name": scheme.get("name"),
                    }
                )

                self.db.add(api_auth)
                return
            
    def _extract_auth_schemes(self, swagger_json: dict):
        """
        Extract authentication schemes from Swagger/OpenAPI
        """

        auth_schemes = {}

        # OpenAPI 3
        components = swagger_json.get("components", {})
        security_schemes = components.get("securitySchemes", {})

        # Swagger 2 fallback
        if not security_schemes:
            security_schemes = swagger_json.get("securityDefinitions", {})

        for name, scheme in security_schemes.items():
            auth_type = scheme.get("type")

            auth_schemes[name] = {
                "type": auth_type,                  # apiKey / http / oauth2
                "scheme": scheme.get("scheme"),     # bearer / basic
                "in": scheme.get("in"),             # header / query
                "name": scheme.get("name"),         # header name (e.g. Authorization)
                "flows": scheme.get("flows"),       # OAuth2
            }

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
    
    def _resolve_schema_ref(self, ref, swagger_json):
        """
        Resolve local $ref like:
        #/components/schemas/User
        """
        parts = ref.strip("#/").split("/")
        ref_obj = swagger_json

        for part in parts:
            ref_obj = ref_obj.get(part, {})

        return ref_obj
    
  
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