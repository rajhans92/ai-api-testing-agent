from fastapi import APIRouter
from app.models.apiParser import (
    SwaggerDocument,
    API,        
    APIParameter,
    APIResponse,
    APIAuth,
    APIDependency,
    ParameterMapping
)
router = APIRouter(prefix="/api-test-agent", tags=["api-test-agent"])

@router.get("/test")
async def test_endpoint():
    return {"message": "API Testing Agent is working!"}