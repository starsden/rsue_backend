from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status, Depends
from typing import List
from uuid import UUID

from app.models.nomen import Nomenclature, NomenclatureCreate, NomenclatureUpdate, NomenclatureResponse, Stock
from app.models.auth import User
from app.models.sklads import Sklads
from app.core.security import get_me


class NomenclatureService:
    def __init__(self, db: Session):
        self.db = db

    def _get_organization_and_sklad(self, current_user: User):
        if not current_user.connect_organization:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not associated with any organization"
            )

        if not current_user.choosen_sklad:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No sklads selected. Please choose a warehouse first."
            )


        sklad = self.db.query(Sklads).filter(
            Sklads.id == current_user.choosen_sklad,
            Sklads.organization_id == current_user.connect_organization,
            Sklads.is_deleted == False
        ).first()

        if not sklad:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Selected sklad does not belong to your organization"
            )

        return current_user.connect_organization, current_user.choosen_sklad

    def create_nomen(self, data: NomenclatureCreate, current_user: User = Depends(get_me)) -> NomenclatureResponse:
        organization_id, sklad_id = self._get_organization_and_sklad(current_user)

        if self.db.query(Nomenclature).filter(
            Nomenclature.article == data.article.upper(),
            Nomenclature.organization_id == organization_id,
            Nomenclature.is_deleted == False
        ).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Article already exists in your organization"
            )

        properties = data.properties.dict() if data.properties else {}
        quantity = data.quantity if data.quantity is not None else 1

        new_item = Nomenclature(
            name=data.name,
            article=data.article.upper(),
            barcode=data.barcode,
            unit=data.unit,
            category_id=data.category_id,
            quantity=quantity,
            properties=properties,
            organization_id=organization_id,
            sklad_id=sklad_id
        )

        try:
            self.db.add(new_item)
            self.db.flush()

            stock_entry = Stock(
                nomenclature_id=new_item.id,
                sklad_id=sklad_id,
                quantity=quantity,
                reserved=0,
                min_quantity=None
            )
            self.db.add(stock_entry)

            self.db.commit()
            self.db.refresh(new_item)
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data integrity error: duplicate barcode or constraint violation"
            ) from e

        return NomenclatureResponse.from_orm(new_item)

    def get_nomen(self, skip: int = 0, limit: int = 100, search: str = None, current_user: User = Depends(get_me)) -> List[NomenclatureResponse]:
        organization_id, sklad_id = self._get_organization_and_sklad(current_user)

        query = self.db.query(Nomenclature).filter(
            Nomenclature.organization_id == organization_id,
            Nomenclature.sklad_id == sklad_id,
            Nomenclature.is_deleted == False
        )

        if search:
            query = query.filter(Nomenclature.name.ilike(f"%{search}%"))

        items = query.offset(skip).limit(limit).all()
        return [NomenclatureResponse.from_orm(item) for item in items]

    def get_nomen_by_id(self, item_id: UUID, current_user: User = Depends(get_me)) -> NomenclatureResponse:
        organization_id, sklad_id = self._get_organization_and_sklad(current_user)

        item = self.db.query(Nomenclature).filter(
            Nomenclature.id == item_id,
            Nomenclature.organization_id == organization_id,
            Nomenclature.sklad_id == sklad_id,
            Nomenclature.is_deleted == False
        ).first()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nomenclature not found in your selected warehouse"
            )

        return NomenclatureResponse.from_orm(item)

    def upd_nomen(self, item_id: UUID, data: NomenclatureUpdate, current_user: User = Depends(get_me)) -> NomenclatureResponse:
        organization_id, sklad_id = self._get_organization_and_sklad(current_user)

        item = self.db.query(Nomenclature).filter(
            Nomenclature.id == item_id,
            Nomenclature.organization_id == organization_id,
            Nomenclature.sklad_id == sklad_id,
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
                    detail="Article already exists in your organization"
                )
            update_dict["article"] = update_dict["article"].upper()

        if "properties" in update_dict and update_dict["properties"] is not None:
            props = update_dict["properties"]
            update_dict["properties"] = props.dict() if hasattr(props, "dict") else props

        if "quantity" in update_dict:
            if update_dict["quantity"] < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quantity cannot be negative"
                )
            stock = self.db.query(Stock).filter(
                Stock.nomenclature_id == item_id,
                Stock.sklad_id == sklad_id
            ).first()
            if stock:
                stock.quantity = update_dict["quantity"]

        for key, value in update_dict.items():
            if key != "quantity":
                setattr(item, key, value)

        self.db.commit()
        self.db.refresh(item)
        return NomenclatureResponse.from_orm(item)

    def del_nomen(self, item_id: UUID, current_user: User = Depends(get_me)) -> dict:
        organization_id, sklad_id = self._get_organization_and_sklad(current_user)

        item = self.db.query(Nomenclature).filter(
            Nomenclature.id == item_id,
            Nomenclature.organization_id == organization_id,
            Nomenclature.sklad_id == sklad_id,
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
        organization_id, sklad_id = self._get_organization_and_sklad(current_user)

        items = self.db.query(Nomenclature).filter(
            Nomenclature.barcode == barcode,
            Nomenclature.organization_id == organization_id,
            Nomenclature.sklad_id == sklad_id,
            Nomenclature.is_deleted == False
        ).all()

        return [NomenclatureResponse.from_orm(item) for item in items]