from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.core import get_db
from app.core.security import get_me
from app.services.orga_service import cr_orga
from app.services.qr_service import QrService
from app.models.orga import OrgaCreate, OrgaResponse, QrCodeResponse, QrCode, Orga, UserInOrgaResponse
from app.models.auth import User
from fastapi import Depends, HTTPException
from uuid import UUID
from typing import List
from datetime import datetime, timedelta, timezone

orga = APIRouter(prefix="/api/orga")
@orga.post("/create", response_model=OrgaResponse, status_code=status.HTTP_201_CREATED, summary="Создать организацию", tags=["Organisation"])
async def create_orga(org_data: OrgaCreate, db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    return cr_orga(db, org_data, user_id=current_user.id)

@orga.get("/", response_model=List[OrgaResponse], summary="Список всех организаций",  tags=["Organisation"])
async def get_all_organizations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    organizations = db.query(Orga).offset(skip).limit(limit).all()
    return [OrgaResponse.from_orm(org) for org in organizations]


@orga.get("/create-qr/{org_id}/", response_model=QrCodeResponse, tags=['QRs'])
async def get_qr(org_id: UUID, expires_in: int = 86400, db: Session = Depends(get_db),current_user = Depends(get_me)):
    org = db.query(Orga).filter(Orga.id == org_id, Orga.user_id == current_user.id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found or access denied")

    qr_service = QrService()
    result = qr_service.create_qr(db, org_id, expires_in)

    return QrCodeResponse(**result)


@orga.get("/join/{token}", tags=['QRs'])
async def join_by(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_me)
):
    qr = db.query(QrCode).filter(
        QrCode.token == token,
        QrCode.is_active == True,
        QrCode.expires_at > datetime.now(timezone.utc)
    ).first()

    if not qr:
        raise HTTPException(status_code=410, detail="QR code is invalid. The otter took him home. ")

    org = db.query(Orga).filter(Orga.id == qr.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Otter did not find such an organization(( ")

    if current_user.connect_organization != str(org.id):
        current_user.connect_organization = str(org.id)
        db.commit()
        db.refresh(current_user)

    qr.is_active = False
    db.commit()

    return {
        "organization": {
            "id": str(org.id),
            "name": org.legalName,
            "inn": org.inn
        },
        "action": "connect",
        "message": f"{current_user.fullName} success connect to '{org.legalName}'"
    }


@orga.get("/{org_id}/members", response_model=List[UserInOrgaResponse], tags=["Organisation"])
async def get_organization_members(
    org_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_me)
):
    org = db.query(Orga).filter(
        Orga.id == org_id,
        Orga.user_id == current_user.id
    ).first()

    if not org:
        raise HTTPException(
            status_code=403,
            detail="Otter thinks that you are not the owner of the organization! She asked me to tell you that she won't give you the data."
        )

    members = db.query(User).filter(
        User.connect_organization == str(org_id)
    ).all()

    return [UserInOrgaResponse.from_orm(m) for m in members]
