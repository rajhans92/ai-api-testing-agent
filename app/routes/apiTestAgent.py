from fastapi import APIRouter

router = APIRouter(prefix="/api-test-agent", tags=["api-test-agent"])

@router.get("/test")
async def test_endpoint():
    return {"message": "API Testing Agent is working!"}