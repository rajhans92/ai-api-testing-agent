from dotenv import load_dotenv
load_dotenv()
import os

API_BASE_NAME = os.getenv("API_BASE_NAME", "api")
API_VERSION = os.getenv("API_VERSION", "v1")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_TOKEN_TIME_HOURS = int(os.getenv("JWT_TOKEN_TIME_HOURS", "5"))
LLM_MODEL = os.getenv("LLM_MODEL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_SSL_MODE = os.getenv("DATABASE_SSL_MODE", "false").lower() == "true"