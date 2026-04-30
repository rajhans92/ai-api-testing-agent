from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional

class ProjectDetails(BaseModel):
   project_name: str
   project_description: Optional[str] = ""


class ParserDetails(BaseModel):
    project_id: int
    swagger_url: HttpUrl

    @field_validator("swagger_url")
    @classmethod
    def validate_swagger_url(cls, v):
        try:
            response = requests.get(str(v), timeout=5)
            response.raise_for_status()
        except Exception as e:
            raise ValueError(f"URL not reachable: {e}")

        try:
            data = response.json()
        except Exception:
            raise ValueError("Response is not valid JSON")

        # Validate Swagger/OpenAPI structure
        if "openapi" not in data and "swagger" not in data:
            raise ValueError("Not a valid Swagger/OpenAPI document")

        if "paths" not in data:
            raise ValueError("Swagger missing 'paths' field")

        return v