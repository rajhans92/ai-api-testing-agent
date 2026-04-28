from pydantic import BaseModel
from typing import Optional

class ProjectDetails(BaseModel):
   project_name: str
   project_description: Optional[str] = ""