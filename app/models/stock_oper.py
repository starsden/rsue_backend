from sqlalchemy import Column, String, Integer, ForeignKey, Enum, DateTime, text
from sqlalchemy.dialects.postgresql import UUID as pgUUID, JSONB
from app.core.core import Base
from pydantic import BaseModel, Field, validator, model_validator
from typing import Optional, Literal
from uuid import UUID, uuid4
from datetime import datetime
import enum

class OperationType(str, enum.Enum):
    TRANSFER = "TRANSFER"
    SALE = "SALE"
    DISPOSAL = "DISPOSAL"
    ADJUSTMENT = "ADJUSTMENT"
    RECEIPT = "RECEIPT"
    RETURN = "RETURN"


class StockOperation(Base):
    __tablename__ = "stockk"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(pgUUID(as_uuid=True), nullable=False, index=True)
    operation_type = Column(Enum(OperationType), nullable=False, index=True)
    
    from_sklad_id = Column(pgUUID(as_uuid=True), ForeignKey("sklads.id", ondelete="SET NULL"), nullable=True, index=True)
    to_sklad_id = Column(pgUUID(as_uuid=True), ForeignKey("sklads.id", ondelete="SET NULL"), nullable=True, index=True)
    nomenclature_id = Column(pgUUID(as_uuid=True), ForeignKey("nomenclature.id", ondelete="CASCADE"), nullable=False, index=True)
    
    quantity = Column(Integer, nullable=False)
    performed_by = Column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    operation_metadata = Column(JSONB, nullable=True, default=dict)
    comment = Column(String, nullable=True)
    
    created_at = Column(DateTime, server_default=text("TIMEZONE('utc', now())"), nullable=False)
    updated_at = Column(DateTime, server_default=text("TIMEZONE('utc', now())"),
                        onupdate=text("TIMEZONE('utc', now())"), nullable=False)

    def __repr__(self):
        return f"<StockOperation(type={self.operation_type}, qty={self.quantity}, nom={self.nomenclature_id})>"


OperationTypeLiteral = Literal["TRANSFER", "SALE", "DISPOSAL", "ADJUSTMENT", "RECEIPT", "RETURN"]


class StockOperationCreate(BaseModel):
    operation_type: OperationTypeLiteral = Field(..., example="TRANSFER")
    nomenclature_id: UUID = Field(..., description="ID номенклатуры")
    quantity: int = Field(..., description="Количество товара (может быть отрицательным для ADJUSTMENT)")
    
    from_sklad_id: Optional[UUID] = Field(None, description="ID склада-источника (для TRANSFER, SALE, DISPOSAL)")
    to_sklad_id: Optional[UUID] = Field(None, description="ID склада-назначения (для TRANSFER, RECEIPT, RETURN)")
    
    comment: Optional[str] = Field(None, max_length=500, description="Комментарий к операции")
    operation_metadata: Optional[dict] = Field(None, description="Дополнительные данные операции")

    @model_validator(mode='after')
    def validate_operation_fields(self):

        if self.operation_type != "ADJUSTMENT" and self.quantity <= 0:
            raise ValueError('quantity must be positive for this operation type')
        if self.operation_type == "ADJUSTMENT" and self.quantity == 0:
            raise ValueError('quantity cannot be zero for ADJUSTMENT')
        if self.operation_type == "TRANSFER":
            if not self.from_sklad_id or not self.to_sklad_id:
                raise ValueError('from_sklad_id and to_sklad_id are required for TRANSFER operation')
            if self.from_sklad_id == self.to_sklad_id:
                raise ValueError('from_sklad_id and to_sklad_id cannot be the same')
        elif self.operation_type in ["SALE", "DISPOSAL"]:
            if not self.from_sklad_id:
                raise ValueError('from_sklad_id is required for SALE and DISPOSAL operations')
        elif self.operation_type in ["RECEIPT", "RETURN"]:
            if not self.to_sklad_id:
                raise ValueError('to_sklad_id is required for RECEIPT and RETURN operations')
        return self


class StockOperationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    operation_type: OperationTypeLiteral
    from_sklad_id: Optional[UUID]
    to_sklad_id: Optional[UUID]
    nomenclature_id: UUID
    quantity: int
    performed_by: Optional[UUID]
    operation_metadata: Optional[dict]
    comment: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

