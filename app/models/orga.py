from sqlalchemy import Column, String, Boolean, text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as pgUUID, JSONB
from app.core.core import Base
from pydantic import BaseModel, Field
from typing import Literal, List
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
    kpp = Column(String, unique=True, index=True)
    address = Column(JSONB, nullable=False, default=dict)
    settings = Column(JSONB, nullable=False, default=dict)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
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
    kpp: str = Field(..., example="123123123")
    address: Address
    settings: Settings

class OrgaResponse(BaseModel):
    id: UUID
    legalName: str
    description: str | None
    inn: str
    kpp: str
    address: dict
    settings: dict

    class Config:
        from_attributes = True

class UserInOrgaResp(BaseModel):
    id: UUID
    fullName: str
    email: str
    role: str | None = None
    connect_organization: str | None = None
    joined_at: datetime | None = None

    class Config:
        from_attributes = True

class UsersInOrg(BaseModel):
    id: UUID
    fullName: str
    email: str
    phone: str | None = None
    joined_at: datetime | None = None

    class Config:
        from_attributes = True

class MyOrga(BaseModel):
    id: UUID
    name: str
    legalName: str
    description: str | None = None
    inn: str
    kpp: str | None = None
    address: dict
    settings: dict
    members_count: int
    members: List[UsersInOrg]
    joined_at: datetime | None = None

    class Config:
        from_attributes = True



class QrCodeResponse(BaseModel):
    qr_image: str  # base64
    join_url: str
    expires_at: datetime
    token: str

    class Config:
        from_attributes = True


class DeleteOrga(BaseModel):
    password: str

class OrgaUpdate(BaseModel):
    legalName: str | None = None
    description: str | None = None
    inn: str | None = None
    kpp: str | None = None
    address: Address | None = None
    settings: Settings | None = None

    class Config:
        from_attributes = True

class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(pgUUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    fullName = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    role = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("TIMEZONE('utc', NOW())"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)

class InvitationCreate(BaseModel):
    email: str
    fullName: str
    phone: str | None = None
    role: str = "User"


class OrganizationInvitationCreate(BaseModel):
    identifier_type: Literal["email", "phone", "full_name"]
    identifier_value: str = Field(..., min_length=1)
    role: str = "User"
    expires_in_hours: int = Field(default=168, ge=1, le=720)


class InvitationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID | None = None
    token: str
    email: str
    fullName: str
    phone: str | None = None
    role: str
    status: Literal["pending", "accepted", "declined", "cancelled"]
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None = None
    responded_at: datetime | None = None

    class Config:
        from_attributes = True


class UserLookupResponse(BaseModel):
    id: UUID
    fullName: str
    email: str
    phone: str | None = None
    role: str | None = None
    connect_organization: str | None = None

    class Config:
        from_attributes = True