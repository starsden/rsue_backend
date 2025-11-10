from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Enum, func
from sqlalchemy.dialects.postgresql import UUID as pgUUID, JSONB
from app.core.core import Base
from uuid import uuid4
import enum
from pydantic import BaseModel, model_validator
from typing import Optional
from uuid import UUID


class DocumentType(str, enum.Enum):
    INVOICE = "invoice"
    CONTRACT = "contract"
    REPORT = "report"
    TTN = "TTN"
    STOCK = "stock"
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Document(Base):
    __tablename__ = "documents"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(pgUUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))

    name = Column(String, nullable=False)
    type = Column(Enum(DocumentType), default=DocumentType.OTHER)
    file_path = Column(String, nullable=False)
    description = Column(String, nullable=True)
    document_metadata = Column(JSONB, nullable=True)

    status = Column(Enum(DocumentStatus), default=DocumentStatus.ACTIVE)
    is_public = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Document(name={self.name}, type={self.type}, org={self.organization_id})>"


class InventoryToken(Base):
    __tablename__ = "inventory_tokens"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(pgUUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    sklad_id = Column(pgUUID(as_uuid=True), ForeignKey("sklads.id", ondelete="CASCADE"), nullable=True, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    signature_hash = Column(String, nullable=False)
    report_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<InventoryToken(org={self.organization_id}, token={self.token[:8]}...)>"


class InventoryReportRequest(BaseModel):
    sklad: bool
    sklad_id: Optional[UUID] = None

    @model_validator(mode='after')
    def validate_sklad_id(self):
        if self.sklad and self.sklad_id is None:
            raise ValueError('sklad_id is required when sklad=True')
        return self


class VerifyByHash(BaseModel):
    signature_hash: str



