from pydantic import BaseModel, Field, validator
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
    fullName = Column(String, unique=True, index=True)
    password = Column(String)
    phone = Column(String)
    role = Column(String, nullable=True)
    companyName = Column(String)
    timezone = Column(String)
    is_active = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)

class UserCreate(BaseModel):
    fullName: str
    email: str
    phone: str
    password: str = Field(max_length=72)
    companyName: str
    role: str = Field(default="User")

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

metadata.create_all(bind=engine)