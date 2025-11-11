from pydantic import BaseModel, Field, EmailStr
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
    phone = Column(String, nullable=True)
    role = Column(String, nullable=True)
    connect_organization = Column(String, nullable=True)
    choosen_sklad = Column(pgUUID, nullable=True)
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
    phone: str | None = None
    password: str = Field(max_length=72)
    companyName: str | None = None
    role: str = Field(default="Founder")

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    choosen_sklad: UUID | None = None

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

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class ChooseSkladRequest(BaseModel):
    sklad_id: UUID = Field(..., description="UUID of choosed")

    class Config:
        json_schema_extra = {
            "example": {
                "sklad_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
            }
        }

class ChooseSkladResponse(BaseModel):
    message: str = "sklad successfully choosen"
    choosen_sklad: UUID

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Склад успешно выбран",
                "choosen_sklad": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
            }
        }



metadata.create_all(bind=engine)