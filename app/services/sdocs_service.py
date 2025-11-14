from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from typing import List
from uuid import UUID

from app.models.sklad_docs import SkladDocument, SkladDocumentItem, SkladDocumentCreate, SkladDocumentUpdate, SkladDocumentResponse, SkladDocumentItemCreate, SkladDocumentItemUpdate, SkladDocumentItemResponse
from app.models.auth import User
from app.models.sklads import Sklads
from app.models.nomen import Nomenclature

class SkladDocumentService:
    def __init__(self, db: Session):
        self.db = db

    def _get_org_id(self, current_user: User) -> UUID:
        if not current_user.connect_organization:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not associated with any organization")
        return UUID(current_user.connect_organization)

    def _validate_sklads(self, sklad_ids: List[UUID], organization_id: UUID):
        sklads = self.db.query(Sklads).filter(Sklads.id.in_(sklad_ids), Sklads.organization_id == organization_id, Sklads.is_deleted == False).all()
        if len(sklads) != len(sklad_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more warehouses not found")
        return sklads

    def create_document(self, data: SkladDocumentCreate, current_user: User) -> SkladDocumentResponse:
        org_id = self._get_org_id(current_user)
        self._validate_sklads(data.sklad_ids, org_id)
        doc = SkladDocument(
            organization_id=org_id,
            created_by=current_user.id,
            sklad_ids=data.sklad_ids,
            doc_type=data.doc_type,
            number=data.number,
            description=data.description,
            address_from=data.address_from.dict() if data.address_from else None,
            address_to=data.address_to.dict() if data.address_to else None
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return SkladDocumentResponse.from_orm(doc)

    def get_documents(self, org_id: UUID, sklad_id: UUID = None) -> List[SkladDocumentResponse]:
        query = self.db.query(SkladDocument).filter(SkladDocument.organization_id == org_id, SkladDocument.is_deleted == False)
        if sklad_id:
            query = query.filter(func.array_position(SkladDocument.sklad_ids, sklad_id) != None)
        return [SkladDocumentResponse.from_orm(d) for d in query.all()]

    def get_document_by_id(self, doc_id: UUID, org_id: UUID) -> SkladDocumentResponse:
        doc = self.db.query(SkladDocument).filter(SkladDocument.id == doc_id, SkladDocument.organization_id == org_id, SkladDocument.is_deleted == False).first()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return SkladDocumentResponse.from_orm(doc)

    def update_document(self, doc_id: UUID, data: SkladDocumentUpdate, org_id: UUID) -> SkladDocumentResponse:
        doc = self.db.query(SkladDocument).filter(SkladDocument.id == doc_id, SkladDocument.organization_id == org_id, SkladDocument.is_deleted == False).first()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        if data.sklad_ids:
            self._validate_sklads(data.sklad_ids, org_id)
        update_dict = data.dict(exclude_unset=True)
        if "address_from" in update_dict and update_dict["address_from"]:
            update_dict["address_from"] = update_dict["address_from"].dict() if hasattr(update_dict["address_from"], "dict") else update_dict["address_from"]
        if "address_to" in update_dict and update_dict["address_to"]:
            update_dict["address_to"] = update_dict["address_to"].dict() if hasattr(update_dict["address_to"], "dict") else update_dict["address_to"]
        for key, value in update_dict.items():
            setattr(doc, key, value)
        self.db.commit()
        self.db.refresh(doc)
        return SkladDocumentResponse.from_orm(doc)

    def delete_document(self, doc_id: UUID, org_id: UUID) -> dict:
        doc = self.db.query(SkladDocument).filter(SkladDocument.id == doc_id, SkladDocument.organization_id == org_id, SkladDocument.is_deleted == False).first()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        doc.is_deleted = True
        self.db.query(SkladDocumentItem).filter(SkladDocumentItem.document_id == doc_id).update({"is_deleted": True})
        self.db.commit()
        return {"message": "Document deleted"}

    def create_item(self, doc_id: UUID, data: SkladDocumentItemCreate, org_id: UUID) -> SkladDocumentItemResponse:
        doc = self.db.query(SkladDocument).filter(SkladDocument.id == doc_id, SkladDocument.organization_id == org_id, SkladDocument.is_deleted == False).first()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        nomen = self.db.query(Nomenclature).filter(
            Nomenclature.id == data.nomenclature_id,
            Nomenclature.organization_id == org_id,
            Nomenclature.is_deleted == False
        ).first()
        if not nomen:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nomenclature not found")
        item = SkladDocumentItem(
            document_id=doc_id,
            nomenclature_id=data.nomenclature_id,
            name=data.name or nomen.name,
            unit=data.unit or nomen.unit,
            packaging=data.packaging.dict() if data.packaging else None,
            quantity_documental=data.quantity_documental,
            quantity_actual=data.quantity_actual,
            is_verified=data.quantity_actual is not None
        )

        if data.quantity_actual is not None:
            nomen.is_verified = True
        
        self.db.add(item)
        self.db.flush()


        all_items = self.db.query(SkladDocumentItem).filter(
            SkladDocumentItem.document_id == doc_id,
            SkladDocumentItem.is_deleted == False
        ).all()
        if all_items and all(item.is_verified for item in all_items):
            doc.is_verified = True
        
        self.db.commit()
        self.db.refresh(item)
        return SkladDocumentItemResponse.from_orm(item)

    def get_items(self, doc_id: UUID, org_id: UUID) -> List[SkladDocumentItemResponse]:
        doc = self.db.query(SkladDocument).filter(SkladDocument.id == doc_id, SkladDocument.organization_id == org_id, SkladDocument.is_deleted == False
        ).first()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        items = self.db.query(SkladDocumentItem).filter(
            SkladDocumentItem.document_id == doc_id,
            SkladDocumentItem.is_deleted == False
        ).all()
        return [SkladDocumentItemResponse.from_orm(i) for i in items]

    def get_item_by_id(self, item_id: UUID, org_id: UUID) -> SkladDocumentItemResponse:
        item = self.db.query(SkladDocumentItem).join(SkladDocument).filter(SkladDocumentItem.id == item_id, SkladDocument.organization_id == org_id, SkladDocumentItem.is_deleted == False).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        return SkladDocumentItemResponse.from_orm(item)

    def update_item(self, item_id: UUID, data: SkladDocumentItemUpdate, org_id: UUID) -> SkladDocumentItemResponse:
        item = self.db.query(SkladDocumentItem).join(SkladDocument).filter(SkladDocumentItem.id == item_id, SkladDocument.organization_id == org_id, SkladDocumentItem.is_deleted == False).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        if data.nomenclature_id:
            nomen = self.db.query(Nomenclature).filter(Nomenclature.id == data.nomenclature_id, Nomenclature.organization_id == org_id, Nomenclature.is_deleted == False).first()
            if not nomen:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nomenclature not found")
        update_dict = data.dict(exclude_unset=True)
        if "packaging" in update_dict and update_dict["packaging"]:
            update_dict["packaging"] = update_dict["packaging"].dict() if hasattr(update_dict["packaging"], "dict") else update_dict["packaging"]

        if "quantity_actual" in update_dict and update_dict["quantity_actual"] is not None:
            item.is_verified = True
            nomen = self.db.query(Nomenclature).filter(Nomenclature.id == item.nomenclature_id).first()
            if nomen:
                nomen.is_verified = True
        
        for key, value in update_dict.items():
            setattr(item, key, value)

        doc = self.db.query(SkladDocument).filter(SkladDocument.id == item.document_id).first()
        if doc:
            all_items = self.db.query(SkladDocumentItem).filter(
                SkladDocumentItem.document_id == doc.id,
                SkladDocumentItem.is_deleted == False
            ).all()
            if all_items and all(item.is_verified for item in all_items):
                doc.is_verified = True
        
        self.db.commit()
        self.db.refresh(item)
        return SkladDocumentItemResponse.from_orm(item)

    def delete_item(self, item_id: UUID, org_id: UUID) -> dict:
        item = self.db.query(SkladDocumentItem).join(SkladDocument).filter(SkladDocumentItem.id == item_id, SkladDocument.organization_id == org_id, SkladDocumentItem.is_deleted == False).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        item.is_deleted = True
        self.db.commit()
        return {"message": "Item deleted"}

