from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Integer, Date, Time, Boolean, MetaData, text, Table, VARCHAR
from sqlalchemy.dialects.postgresql import UUID as pgUUID
import uuid
from datetime import date, time, datetime
from app.core.core import Base, engine
from uuid import UUID, uuid4


metadata = MetaData()

class User(Base):
    __tablename__ = "users"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True)
    fullName = Column(String, index=True)
    password = Column(String)
    phone = Column(String)
    role = Column(String, nullable=True)
    connect_organization = Column(String, nullable=True)
    companyName = Column(String, nullable=True)
    timezone = Column(String)
    is_active = Column(Boolean, default=False)
    ver_code = Column(String, nullable=True)
    code_expires_at = Column(DateTime, nullable=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)

class UserCreate(BaseModel):
    fullName: str
    email: str
    phone: str
    password: str = Field(max_length=72)
    companyName: str | None = None
    role: str = Field(default="Founder")

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: str
    password: str
    class Config:
        json_schema_extra = {
            "example": {
                "email": "string",
                "password": "string",
            }
        }


class UserResponse(BaseModel):
    id: str
    username: str
    email: str

    class Config:
        from_attributes = True

class TokenData(BaseModel):
    email: str | None = None

class VerifyEmailRequest(BaseModel):
    email: str
    code: str

metadata.create_all(bind=engine)