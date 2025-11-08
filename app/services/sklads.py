# app/services/sklad_service.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from app.models.sklads import Sklads, SkladsCreate, SkladsUpdate, SkladsResponse
from typing import List
from uuid import UUID


class SkladService:
    def __init__(self, db: Session):
        self.db = db

    def create_sklad(
        self,
        sklad_data: SkladsCreate,
        organization_id: UUID
    ) -> SkladsResponse:
        if self.db.query(Sklads).filter(
            Sklads.code == sklad_data.code,
            Sklads.is_deleted == False
        ).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="sklad already exists"
            )

        address = sklad_data.address.dict() if sklad_data.address else {}
        contact_person = sklad_data.contact_person.dict() if sklad_data.contact_person else None
        settings = sklad_data.settings.dict() if sklad_data.settings else {
            "allowNegativeStock": False,
            "requireApproval": True,
            "autoPrintLabels": True,
            "barcodeType": "EAN13"
        }

        new_sklad = Sklads(
            name=sklad_data.name,
            code=sklad_data.code.upper(),
            type=sklad_data.type,
            address=address,
            contact_person=contact_person,
            settings=settings,
            organization_id=organization_id
        )

        try:
            self.db.add(new_sklad)
            self.db.commit()
            self.db.refresh(new_sklad)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="data error"
            )

        return SkladsResponse.from_orm(new_sklad)

    def get_sklads(self, organization_id: UUID, skip: int = 0, limit: int = 100) -> List[SkladsResponse]:
        sklads = (
            self.db.query(Sklads)
            .filter( Sklads.organization_id == organization_id, Sklads.is_deleted == False)
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [SkladsResponse.from_orm(sklad) for sklad in sklads]

    def get_sklad_by_id(
        self,
        sklad_id: UUID,
        organization_id: UUID
    ) -> SkladsResponse:
        sklad = self.db.query(Sklads).filter(
            Sklads.id == sklad_id,
            Sklads.organization_id == organization_id,
            Sklads.is_deleted == False
        ).first()

        if not sklad:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The otter got lost"
            )

        return SkladsResponse.from_orm(sklad)

    def update_sklad(
        self,
        sklad_id: UUID,
        update_data: SkladsUpdate,
        organization_id: UUID
    ) -> SkladsResponse:
        sklad = self.db.query(Sklads).filter(
            Sklads.id == sklad_id,
            Sklads.organization_id == organization_id,
            Sklads.is_deleted == False
        ).first()

        if not sklad:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="sklad not found"
            )

        update_dict = update_data.dict(exclude_unset=True)

        if "code" in update_dict:
            existing = self.db.query(Sklads).filter(
                Sklads.code == update_dict["code"],
                Sklads.id != sklad_id,
                Sklads.is_deleted == False
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="sklad already exists"
                )
            update_dict["code"] = update_dict["code"].upper()

        for key, value in update_dict.items():
            if value is not None:
                setattr(sklad, key, value)

        self.db.commit()
        self.db.refresh(sklad)
        return SkladsResponse.from_orm(sklad)

    def delete_sklad(
        self,
        sklad_id: UUID,
        organization_id: UUID
    ) -> dict:
        sklad = self.db.query(Sklads).filter(
            Sklads.id == sklad_id,
            Sklads.organization_id == organization_id,
            Sklads.is_deleted == False
        ).first()

        if not sklad:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="sklad not found"
            )

        sklad.is_deleted = True
        self.db.commit()

        return {"message": "sklad successfully deleted"}