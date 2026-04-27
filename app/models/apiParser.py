import uuid
from datetime import datetime

from sqlalchemy import (
    Integer,
    Column,
    String,
    Text,
    Boolean,
    ForeignKey,
    TIMESTAMP
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.utils.database import Base


# -------------------------
# Projects
# -------------------------
class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    description = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    swagger_documents = relationship("SwaggerDocument", back_populates="project")


# -------------------------
# Swagger Documents
# -------------------------
class SwaggerDocument(Base):
    __tablename__ = "swagger_documents"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    version = Column(String(50))
    raw_json = Column(JSONB)
    parsed_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    project = relationship("Project", back_populates="swagger_documents")
    apis = relationship("API", back_populates="swagger_documents")


# -------------------------
# APIs
# -------------------------
class API(Base):
    __tablename__ = "apis"

    id = Column(Integer, primary_key=True, index=True)
    swagger_id = Column(Integer, ForeignKey("swagger_documents.id"), nullable=False)
    operation_id = Column(String(255))
    method = Column(String(10))
    path = Column(Text)
    summary = Column(Text)
    description = Column(Text)
    tag = Column(String(100))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    swagger = relationship("SwaggerDocument", back_populates="apis")
    parameters = relationship("APIParameter", back_populates="apis")
    responses = relationship("APIResponse", back_populates="apis")
    auth = relationship("APIAuth", back_populates="apis", uselist=False)

    dependencies_source = relationship(
        "APIDependency",
        foreign_keys="APIDependency.source_api_id",
        back_populates="source_api"
    )

    dependencies_target = relationship(
        "APIDependency",
        foreign_keys="APIDependency.target_api_id",
        back_populates="target_api"
    )


# -------------------------
# API Parameters
# -------------------------
class APIParameter(Base):
    __tablename__ = "api_parameters"

    id = Column(Integer, primary_key=True, index=True)
    api_id = Column(Integer, ForeignKey("apis.id"), nullable=False)
    name = Column(String(255))
    location = Column(String(50))  # path, query, header, body
    type = Column(String(50))
    required = Column(Boolean)
    schema = Column(JSONB)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    api = relationship("API", back_populates="parameters")


# -------------------------
# API Responses
# -------------------------
class APIResponse(Base):
    __tablename__ = "api_responses"

    id = Column(Integer, primary_key=True, index=True)
    api_id = Column(Integer, ForeignKey("apis.id"), nullable=False)
    status_code = Column(String(10))
    schema = Column(JSONB)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    api = relationship("API", back_populates="responses")


# -------------------------
# API Auth
# -------------------------
class APIAuth(Base):
    __tablename__ = "api_auth"

    id = Column(Integer, primary_key=True, index=True)
    api_id = Column(Integer, ForeignKey("apis.id"), nullable=False)
    auth_type = Column(String(50))  # bearer, apiKey, oauth
    config = Column(JSONB)

    api = relationship("API", back_populates="auth")


# -------------------------
# API Dependencies
# -------------------------
class APIDependency(Base):
    __tablename__ = "api_dependencies"

    id = Column(Integer, primary_key=True, index=True)
    source_api_id = Column(Integer, ForeignKey("apis.id"), nullable=False)
    target_api_id = Column(Integer, ForeignKey("apis.id"), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    source_api = relationship(
        "API",
        foreign_keys=[source_api_id],
        back_populates="dependencies_source"
    )

    target_api = relationship(
        "API",
        foreign_keys=[target_api_id],
        back_populates="dependencies_target"
    )

    mappings = relationship("ParameterMapping", back_populates="dependency")


# -------------------------
# Parameter Mappings
# -------------------------
class ParameterMapping(Base):
    __tablename__ = "parameter_mappings"

    id = Column(Integer, primary_key=True, index=True)
    dependency_id = Column(Integer, ForeignKey("api_dependencies.id"), nullable=False)
    source_field = Column(String(255))
    target_field = Column(String(255))
    source_location = Column(String(50))  # response/body
    target_location = Column(String(50))  # path/query/body
    transformation = Column(JSONB)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    dependency = relationship("APIDependency", back_populates="mappings")