from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from uuid import UUID
from datetime import datetime, timezone, timedelta

from app.models.offline import OfflineToken, OfflineDevice, OfflineTokenCreate, OfflineTokenResponse
from app.models.sklads import Sklads
from app.models.auth import User
from app.models.nomen import Nomenclature, NomenclatureResponse
from app.models.sklad_docs import SkladDocument, SkladDocumentItem, SkladDocumentResponse, SkladDocumentItemResponse
from app.utils.qr import generate_token, make_qr_base64


class OfflineService:
    def __init__(self, db: Session):
        self.db = db

    def _get_org(self, current_user: User) -> UUID:
        if not current_user.connect_organization:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not associated with any organization")
        return UUID(current_user.connect_organization)

    def _validate_sklad(self, sklad_id: UUID, organization_id: UUID | None = None) -> Sklads:
        query = self.db.query(Sklads).filter(Sklads.id == sklad_id, Sklads.is_deleted == False)
        if organization_id:
            query = query.filter(Sklads.organization_id == organization_id)
        sklad = query.first()
        if not sklad:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
        return sklad

    def create_token(self, sklad_id: UUID, payload: OfflineTokenCreate, current_user: User) -> OfflineTokenResponse:
        org_id = self._get_org(current_user)
        sklad = self._validate_sklad(sklad_id, org_id)
        self.db.query(OfflineToken).filter(
            OfflineToken.sklad_id == sklad_id,
            OfflineToken.is_active == True
        ).update({"is_active": False})
        token = generate_token()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=payload.expires_in) if payload.expires_in else None
        offline_token = OfflineToken(
            organization_id=sklad.organization_id,
            sklad_id=sklad_id,
            created_by=current_user.id,
            token=token,
            expires_at=expires_at,
            is_active=True
        )
        self.db.add(offline_token)
        self.db.commit()
        self.db.refresh(offline_token)
        url = f"https://rsue.devoriole.ru/api/offline/sklad?token={token}"
        qr_image = make_qr_base64(url)
        return OfflineTokenResponse(
            token=token,
            expires_at=expires_at,
            qr_url=url,
            qr_image=f"data:image/svg+xml;base64,{qr_image}"
        )

    def _get_active_token(self, token: str) -> OfflineToken:
        offline_token = self.db.query(OfflineToken).filter(OfflineToken.token == token, OfflineToken.is_active == True).first()
        if not offline_token:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offline token not found")
        if offline_token.expires_at and datetime.now(timezone.utc) > offline_token.expires_at:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Offline token expired")
        return offline_token

    def get_sklad_data(self, token: str, device_id: str) -> dict:
        offline_token = self._get_active_token(token)
        sklad = self.db.query(Sklads).filter(Sklads.id == offline_token.sklad_id).first()
        if not sklad:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

        device = self.db.query(OfflineDevice).filter(
            OfflineDevice.token_id == offline_token.id,
            OfflineDevice.device_id == device_id,
            OfflineDevice.is_active == True
        ).first()

        if device:
            device.is_active = False
            device.last_seen = datetime.now(timezone.utc)
            self.db.commit()
            return {"message": "Exit registred! Thank you for your working! <3"}

        device_record = self.db.query(OfflineDevice).filter(
            OfflineDevice.token_id == offline_token.id,
            OfflineDevice.device_id == device_id
        ).first()

        if device_record:
            device_record.is_active = True
            device_record.last_seen = datetime.now(timezone.utc)
        else:
            device_record = OfflineDevice(
                token_id=offline_token.id,
                device_id=device_id,
                is_active=True
            )
            self.db.add(device_record)
        self.db.commit()

        nomenclature = self.db.query(Nomenclature).filter(
            Nomenclature.organization_id == offline_token.organization_id,
            Nomenclature.sklad_id == offline_token.sklad_id,
            Nomenclature.is_deleted == False
        ).all()
        nomenclature_payload = [NomenclatureResponse.from_orm(item).model_dump() for item in nomenclature]

        documents = self.db.query(SkladDocument).filter(
            SkladDocument.organization_id == offline_token.organization_id,
            SkladDocument.is_deleted == False,
            func.array_position(SkladDocument.sklad_ids, offline_token.sklad_id) != None
        ).all()

        documents_payload = []
        for doc in documents:
            doc_resp = SkladDocumentResponse.from_orm(doc).model_dump()
            items = self.db.query(SkladDocumentItem).filter(
                SkladDocumentItem.document_id == doc.id,
                SkladDocumentItem.is_deleted == False
            ).all()
            doc_resp["items"] = [SkladDocumentItemResponse.from_orm(item).model_dump() for item in items]
            documents_payload.append(doc_resp)

        return {
            "token": token,
            "sklad": {
                "id": str(sklad.id),
                "name": sklad.name,
                "code": sklad.code,
                "type": sklad.type,
                "address": sklad.address,
                "organization_id": str(sklad.organization_id)
            },
            "nomenclature": nomenclature_payload,
            "documents": documents_payload
        }


