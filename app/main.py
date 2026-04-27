from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from app.routes.apiTestAgent import router as api_test_agent_router
from app.utils.database import engine, Base
from app.utils.exceptional import (
    http_exception_handler,
    validation_exception_handler,
    value_error_handler,
    global_exception_handler
)
from app.utils.config import (
    API_VERSION,
    API_BASE_NAME
)
app = FastAPI()

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(Exception, global_exception_handler)

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(api_test_agent_router, prefix=f'/{API_BASE_NAME}/{API_VERSION}')

@app.get("/")
async def root():
    return {"message": "API Testing Agent is running!"}