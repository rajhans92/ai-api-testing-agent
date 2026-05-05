from pydantic import BaseModel
from typing import List 

class Dependency(BaseModel):
    api_id: int
    depends_on_api_id: int

class DependencyResponse(BaseModel):
    dependencies: List[Dependency]