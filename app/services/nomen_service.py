from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status, Depends
from typing import List
from uuid import UUID

from app.models.nomen import Nomenclature, NomenclatureCreate, NomenclatureUpdate, NomenclatureResponse
from app.models.auth import User
from app.core.security import get_me


class NomenclatureService:
    def __init__(self, db: Session):
        self.db = db

    def _get_organization_id(self, current_user: User) -> UUID:
        if not current_user.connect_organization:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not associated with any organization"
            )
        return current_user.connect_organization

    def create_nomen(self, data: NomenclatureCreate, current_user: User = Depends(get_me)) -> NomenclatureResponse:
        organization_id = self._get_organization_id(current_user)

        if self.db.query(Nomenclature).filter(
            Nomenclature.article == data.article.upper(),
            Nomenclature.organization_id == organization_id,
            Nomenclature.is_deleted == False
        ).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Article already exists"
            )

        properties = data.properties.dict() if data.properties else {}

        new_item = Nomenclature(
            name=data.name,
            article=data.article.upper(),
            barcode=data.barcode,
            unit=data.unit,
            category_id=data.category_id,
            properties=properties,
            organization_id=organization_id
        )

        try:
            self.db.add(new_item)
            self.db.commit()
            self.db.refresh(new_item)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data error"
            )

        return NomenclatureResponse.from_orm(new_item)

    def get_nomen(self, skip: int = 0, limit: int = 100, search: str = None, current_user: User = Depends(get_me)) -> List[NomenclatureResponse]:
        organization_id = self._get_organization_id(current_user)

        query = self.db.query(Nomenclature).filter(
            Nomenclature.organization_id == organization_id,
            Nomenclature.is_deleted == False
        )

        if search:
            query = query.filter(Nomenclature.name.ilike(f"%{search}%"))

        items = query.offset(skip).limit(limit).all()
        return [NomenclatureResponse.from_orm(item) for item in items]

    def get_nomen_by_id(self, item_id: UUID, current_user: User = Depends(get_me)) -> NomenclatureResponse:
        organization_id = self._get_organization_id(current_user)

        item = self.db.query(Nomenclature).filter(
            Nomenclature.id == item_id,
            Nomenclature.organization_id == organization_id,
            Nomenclature.is_deleted == False
        ).first()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nomenclature not found"
            )

        return NomenclatureResponse.from_orm(item)

    def upd_nomen(self, item_id: UUID, data: NomenclatureUpdate, current_user: User = Depends(get_me)) -> NomenclatureResponse:
        organization_id = self._get_organization_id(current_user)

        item = self.db.query(Nomenclature).filter(
            Nomenclature.id == item_id,
            Nomenclature.organization_id == organization_id,
            Nomenclature.is_deleted == False
        ).first()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nomenclature not found"
            )

        update_dict = data.dict(exclude_unset=True)

        if "article" in update_dict:
            existing = self.db.query(Nomenclature).filter(
                Nomenclature.article == update_dict["article"].upper(),
                Nomenclature.id != item_id,
                Nomenclature.organization_id == organization_id,
                Nomenclature.is_deleted == False
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Article already exists"
                )
            update_dict["article"] = update_dict["article"].upper()

        if "properties" in update_dict and update_dict["properties"] is not None:
            props = update_dict["properties"]
            if hasattr(props, "dict"):
                update_dict["properties"] = props.dict()

        for key, value in update_dict.items():
            setattr(item, key, value)

        self.db.commit()
        self.db.refresh(item)
        return NomenclatureResponse.from_orm(item)

    def del_nomen(self, item_id: UUID, current_user: User = Depends(get_me)) -> dict:
        organization_id = self._get_organization_id(current_user)

        item = self.db.query(Nomenclature).filter(
            Nomenclature.id == item_id,
            Nomenclature.organization_id == organization_id,
            Nomenclature.is_deleted == False
        ).first()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nomenclature not found"
            )

        item.is_deleted = True
        self.db.commit()
        return {"message": "Nomenclature successfully deleted"}

    def search(self, barcode: str, current_user: User = Depends(get_me)) -> List[NomenclatureResponse]:
        organization_id = self._get_organization_id(current_user)

        items = self.db.query(Nomenclature).filter(
            Nomenclature.barcode == barcode,
            Nomenclature.organization_id == organization_id,
            Nomenclature.is_deleted == False
        ).all()
        return [NomenclatureResponse.from_orm(item) for item in items]