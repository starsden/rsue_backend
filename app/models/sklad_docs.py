from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Enum, Integer, text
from sqlalchemy.dialects.postgresql import UUID as pgUUID, JSONB, ARRAY
from app.core.core import Base
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime
import enum

class SkladDocumentType(str, enum.Enum):
    OUTGOING = "outgoing"
    INCOMING = "incoming"
    INVENTORY = "inventory"

class SkladDocument(Base):
    __tablename__ = "sklad_doc"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(pgUUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sklad_ids = Column(ARRAY(pgUUID), nullable=False, index=True)
    doc_type = Column(Enum(SkladDocumentType), nullable=False, index=True)
    number = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("TIMEZONE('utc', now())"), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=text("TIMEZONE('utc', now())"), onupdate=text("TIMEZONE('utc', now())"), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

class SkladDocumentItem(Base):
    __tablename__ = "sklad_doc_items"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(pgUUID(as_uuid=True), ForeignKey("sklad_doc.id", ondelete="CASCADE"), nullable=False, index=True)
    nomenclature_id = Column(pgUUID(as_uuid=True), ForeignKey("nomenclature.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("TIMEZONE('utc', now())"), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=text("TIMEZONE('utc', now())"), onupdate=text("TIMEZONE('utc', now())"), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

class SkladDocumentCreate(BaseModel):
    sklad_ids: List[UUID]
    doc_type: SkladDocumentType
    number: str
    description: Optional[str] = None

class SkladDocumentUpdate(BaseModel):
    sklad_ids: Optional[List[UUID]] = None
    doc_type: Optional[SkladDocumentType] = None
    number: Optional[str] = None
    description: Optional[str] = None

class SkladDocumentItemCreate(BaseModel):
    nomenclature_id: UUID
    quantity: int = Field(..., ge=1)

class SkladDocumentItemUpdate(BaseModel):
    nomenclature_id: Optional[UUID] = None
    quantity: Optional[int] = Field(None, ge=1)

class SkladDocumentItemResponse(BaseModel):
    id: UUID
    document_id: UUID
    nomenclature_id: UUID
    quantity: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SkladDocumentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    created_by: Optional[UUID]
    sklad_ids: List[UUID]
    doc_type: SkladDocumentType
    number: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    class Config:
        from_attributes = True

