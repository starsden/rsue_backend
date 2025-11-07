from sqlalchemy import Column, String, Boolean, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as pgUUID, JSONB
from app.core.core import Base
from pydantic import BaseModel, Field
from typing import Literal
import uuid
from uuid import UUID

class Orga(Base):
    __tablename__ = "organisations"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(pgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    legalName = Column(String, nullable=False)
    description = Column(String)
    inn = Column(String, unique=True, index=True)
    address = Column(JSONB, nullable=False, default=dict)
    settings = Column(JSONB, nullable=False, default=dict)

    def __repr__(self):
        return f"<Orga {self.name} ({self.legalName})>"


class Address(BaseModel):
    country: str
    city: str
    street: str
    postalCode: str

class Settings(BaseModel):
    currency: str = Field(..., example="RUB")
    language: str = Field(..., example="ru")
    timezone: str = Field(..., example="Europe/Moscow")
    autoBackup: bool = Field(..., example=True)
    backupFrequency: Literal["DAILY", "WEEKLY", "MONTHLY"] = Field(..., example="DAILY")

class OrgaCreate(BaseModel):
    name: str = Field(..., example="Oriole")
    legalName: str = Field(..., example="ООО РИОЛ")
    description: str | None = Field(None, example="Команда разработчиков")
    inn: str = Field(..., example="1234567890")
    address: Address
    settings: Settings

class OrgaResponse(BaseModel):
    id: UUID
    legalName: str
    description: str | None
    inn: str
    address: dict
    settings: dict

    class Config:
        from_attributes = True