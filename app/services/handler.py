from fastapi import Depends
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.services.apiParser import APIParserService


def get_api_parser_service(db: Session = Depends(get_db)):
    return APIParserService(db)

