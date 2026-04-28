from fastapi import APIRouter, HTTPException, Depends
from app.schemas.apiParser import (
    ProjectDetails,
)
from app.services.handler import (
    get_api_parser_service,
)
from app.services.apiParser import APIParserService

router = APIRouter(prefix="/api-test-agent", tags=["api-test-agent"])

@router.post("/project")
async def create_project(project: ProjectDetails, apiParseService: APIParserService = Depends(get_api_parser_service)):
    try:
        project_id = await apiParseService.create_project(project)
        return {"message": "Project created successfully", "project_id": project_id}
    except Exception as e:
        print("Error creating project: ", str(e))
        raise HTTPException(status_code=500, detail="Failed to create project")  
    