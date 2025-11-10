from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Enum, func
from sqlalchemy.dialects.postgresql import UUID as pgUUID, JSONB
from app.core.core import Base
from uuid import uuid4
import enum


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
    metadata = Column(JSONB, nullable=True)

    status = Column(Enum(DocumentStatus), default=DocumentStatus.ACTIVE)
    is_public = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Document(name={self.name}, type={self.type}, org={self.organization_id})>"
