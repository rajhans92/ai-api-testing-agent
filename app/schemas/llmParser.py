from pydantic import BaseModel
from typing import List

class Dependency(BaseModel):
    api_id: str
    depends_on_api_id: str

class DependencyResponse(BaseModel):
    dependencies: List[Dependency]