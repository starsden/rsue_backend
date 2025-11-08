from sqlalchemy import Column, String, Boolean, text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as pgUUID, JSONB
from app.core.core import Base
from pydantic import BaseModel, Field
from typing import Literal
import uuid
from datetime import date, time, datetime
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

class QrCode(Base):
    __tablename__ = "qrs"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(pgUUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now)
    created_at = Column(DateTime(timezone=True), server_default=text("TIMEZONE('utc', NOW())"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    def __repr__(self):
        return f"<QrCode org={self.organization_id} expires={self.expires_at}>"

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

class UserInOrgaResponse(BaseModel):
    id: UUID
    fullName: str
    email: str
    role: str | None = None
    connect_organization: str | None = None

    class Config:
        from_attributes = True



class QrCodeResponse(BaseModel):
    qr_image: str  # base64
    join_url: str
    expires_at: datetime
    token: str

    class Config:
        from_attributes = True
        