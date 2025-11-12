from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from app.core.core import Base
from pydantic import BaseModel, Field
from typing import Optional
from uuid import uuid4, UUID
from datetime import datetime, timezone


class OfflineToken(Base):
    __tablename__ = "offline_sklad_tokens"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(pgUUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    sklad_id = Column(pgUUID(as_uuid=True), ForeignKey("sklads.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class OfflineDevice(Base):
    __tablename__ = "offline_devices"
    __table_args__ = (UniqueConstraint("token_id", "device_id", name="uq_offline_device"),)

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid4)
    token_id = Column(pgUUID(as_uuid=True), ForeignKey("offline_sklad_tokens.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    first_seen = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class OfflineTokenCreate(BaseModel):
    expires_in: int = Field(86400, ge=60, le=604800, description="Seconds until token expiration")


class OfflineTokenResponse(BaseModel):
    token: str
    expires_at: Optional[datetime]
    qr_url: str
    qr_image: str

    class Config:
        from_attributes = True

