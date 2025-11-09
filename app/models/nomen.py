from sqlalchemy import Column, String, Boolean, text, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID as pgUUID, JSONB
from app.core.core import Base
from pydantic import BaseModel, Field, validator
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

class Nomenclature(Base):
    __tablename__ = "nomenclature"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(200), nullable=False, index=True)
    article = Column(String(50), nullable=False, unique=True, index=True)
    barcode = Column(String(50), nullable=True, unique=True, index=True)
    unit = Column(String(20), nullable=False, default="pcs")
    quantity = Column(Integer, nullable=False, default=1)
    category_id = Column(String, nullable=True, index=True)
    properties = Column(JSONB, nullable=True, default=dict)
    organization_id = Column(pgUUID(as_uuid=True), nullable=False, index=True)
    sklad_id = Column(pgUUID(as_uuid=True), nullable=False, index=True)

    created_at = Column(DateTime, server_default=text("TIMEZONE('utc', now())"), nullable=False)
    updated_at = Column(DateTime, server_default=text("TIMEZONE('utc', now())"),
                        onupdate=text("TIMEZONE('utc', now())"), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<Nomenclature {self.name} ({self.article})>"

class Stock(Base):
    __tablename__ = "stock"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid4)
    nomenclature_id = Column(pgUUID(as_uuid=True), ForeignKey("nomenclature.id"), nullable=False, index=True)
    sklad_id = Column(pgUUID(as_uuid=True), ForeignKey("sklads.id"), nullable=False, index=True)

    quantity = Column(Integer, nullable=False, default=0)
    reserved = Column(Integer, nullable=False, default=0)
    min_quantity = Column(Integer, nullable=True)

    created_at = Column(DateTime, server_default=text("TIMEZONE('utc', now())"), nullable=False)
    updated_at = Column(DateTime, server_default=text("TIMEZONE('utc', now())"), onupdate=text("TIMEZONE('utc', now())"), nullable=False)



class NomenclatureProperties(BaseModel):
    brand: Optional[str] = Field(None, example="Простоквашино")
    fat: Optional[str] = Field(None, example="3.2%")
    volume: Optional[str] = Field(None, example="1л")
    shelf_life: Optional[str] = Field(None, example="7 дней")


class NomenclatureCreate(BaseModel):
    name: str = Field(..., example="Молоко Простоквашино 3.2%")
    article: str = Field(..., example="MLK-001")
    barcode: Optional[str] = Field(None, example="4601234567890")
    quantity: Optional[int] = Field(None, example=1)
    unit: str = Field("pcs", example="pcs")
    category_id: str = Field(..., example="Молочные продукты")
    properties: Optional[NomenclatureProperties] = None

    @validator("article")
    def article_uppercase(cls, v):
        return v.upper()


class NomenclatureUpdate(BaseModel):
    name: Optional[str] = Field(None)
    article: Optional[str] = Field(None)
    barcode: Optional[str] = Field(None)
    quantity: Optional[int] = Field(None)
    unit: Optional[str] = Field(None)
    category_id: Optional[str] = None
    properties: Optional[NomenclatureProperties] = None


class NomenclatureResponse(BaseModel):
    id: UUID
    name: str
    article: str
    barcode: Optional[str]
    unit: str
    quantity: int
    category_id: Optional[str]
    properties: Optional[NomenclatureProperties]
    organization_id: UUID
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    class Config:
        from_attributes = True



class StockCreate(BaseModel):
    nomenclature_id: UUID
    sklad_id: UUID
    quantity: int = Field(..., ge=0)
    reserved: Optional[int] = Field(0, ge=0)
    min_quantity: Optional[int] = Field(None, ge=0)

class StockUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=0)
    reserved: Optional[int] = Field(None, ge=0)
    min_quantity: Optional[int] = Field(None, ge=0)

class StockResponse(BaseModel):
    id: UUID
    nomenclature_id: UUID
    sklad_id: UUID
    quantity: int
    reserved: int
    min_quantity: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True