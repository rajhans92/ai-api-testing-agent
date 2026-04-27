from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.utils.config import (
    DATABASE_USER,
    DATABASE_PASSWORD,
    DATABASE_HOST,
    DATABASE_NAME,
    DATABASE_SSL_MODE
) 
import ssl
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

connect_args = {}

databaseConntUrl = f"postgresql+asyncpg://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}/{DATABASE_NAME}"

if DATABASE_SSL_MODE.lower() == "true":
    databaseConntUrl += "?sslmode=require"
    connect_args["ssl"] = ssl_context

engine = create_async_engine(databaseConntUrl,connect_args=connect_args)
sessionLocal = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    print("DB connected stabilist")
    try:
        async with sessionLocal() as db:
            yield db
    finally:
        await db.close()