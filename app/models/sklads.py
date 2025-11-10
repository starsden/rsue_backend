from sqlalchemy import Column, String, Boolean, Enum, text, DateTime
from sqlalchemy.dialects.postgresql import UUID as pgUUID, JSONB
from app.core.core import Base
from pydantic import BaseModel, Field, EmailStr, validator, model_validator
from typing import Literal, Optional
import uuid
from uuid import UUID
from datetime import datetime

WarehouseType = Literal["MAIN", "RETAIL", "TRANSIT", "QUARANTINE"]
class Sklads(Base):
    __tablename__ = "sklads"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    type = Column(Enum("MAIN", "RETAIL", "TRANSIT", "QUARANTINE", name="warehouse_type"), nullable=False)

    address = Column(JSONB, nullable=False)
    contact_person = Column(JSONB, nullable=True)
    settings = Column(JSONB, nullable=False, default=dict)

    organization_id = Column(pgUUID(as_uuid=True), nullable=False, index=True)

    created_at = Column(DateTime, server_default=text("TIMEZONE('utc', now())"), nullable=False)
    updated_at = Column(DateTime, server_default=text("TIMEZONE('utc', now())"),
                        onupdate=text("TIMEZONE('utc', now())"), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    def __repr__(self):
        return f"<Sklad {self.name} ({self.code})>"



class AddressSchema(BaseModel):
    country: str = Field(..., example="Россия")
    city: str = Field(..., example="Екатеринбург")
    street: str = Field(..., example="ул. Складская, 45")
    postalCode: str = Field(..., example="123456")


class ContactPerson(BaseModel):
    name: str = Field(..., example="Йоп Ян")
    phone: str = Field(..., example="+79123456789")
    email: Optional[EmailStr] = Field(None, example="warehouse@example.com")


class SkladsSettings(BaseModel):
    allowNegativeStock: bool = Field(False, example=False)
    requireApproval: bool = Field(True, example=True)
    autoPrintLabels: bool = Field(True, example=True)
    barcodeType: str = Field("EAN13", example="EAN13")

class SkladsCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100, example="Основной склад")
    code: str = Field(..., min_length=3, max_length=50, example="MAIN_WH")
    type: WarehouseType = Field(..., example="MAIN")

    address: AddressSchema
    contact_person: Optional[ContactPerson] = None
    settings: Optional[SkladsSettings] = None

    @validator("code")
    def code_uppercase(cls, v):
        return v.upper()

class SkladsUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    code: Optional[str] = Field(None, min_length=3, max_length=50)
    type: Optional[WarehouseType] = None
    address: Optional[AddressSchema] = None
    contact_person: Optional[ContactPerson] = None
    settings: Optional[SkladsSettings] = None

class SkladsResponse(BaseModel):
    id: UUID
    name: str
    code: str
    type: WarehouseType
    address: AddressSchema
    contact_person: Optional[ContactPerson]
    settings: SkladsSettings
    organization_id: UUID
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    class Config:
        from_attributes = True