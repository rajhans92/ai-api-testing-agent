from fastapi import APIRouter, HTTPException, Depends
from app.schemas.apiParser import (
    ProjectDetails,
    ParserDetails
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
    
@router.get("/project/{project_id}")
async def get_project(project_id: int, apiParseService: APIParserService = Depends(get_api_parser_service)):
    try:
        project = await apiParseService.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"message":"Get Project deatils successfully","detail": project}
    except HTTPException as he:
        raise he
    except Exception as e:
        print("Error fetching project: ", str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch project")   

@router.post("/parse-api-doc")
async def parse_swagger(parserDetails: ParserDetails, apiParseService: APIParserService = Depends(get_api_parser_service)):
    try:
        swaggerData = apiParseService.parse_swagger(parserDetails.swagger_url, parserDetails.project_id)
        return {"message": "Swagger parsed successfully"}
    except Exception as e:
        print("Error parsing swagger: ", str(e))
        raise HTTPException(status_code=500, detail="Failed to parse swagger")