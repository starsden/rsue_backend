from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.core import get_db
from app.core.security import get_me
from app.services.orga_service import cr_orga
from app.services.qr_service import QrService
from app.models.orga import OrgaCreate, OrgaResponse, QrCodeResponse, QrCode, Orga
from app.models.auth import User
from fastapi import Depends, HTTPException
from uuid import UUID
from datetime import datetime, timedelta, timezone

orga = APIRouter(prefix="/api/orga", tags=["organisation"])
@orga.post("/create", response_model=OrgaResponse, status_code=status.HTTP_201_CREATED, summary="Создать организацию (требуется авторизация)")
async def create_orga(org_data: OrgaCreate, db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    return cr_orga(db, org_data, user_id=current_user.id)

@orga.get("/create-qr/{org_id}", response_model=QrCodeResponse)
async def get_qr_code(org_id: UUID, expires_in: int = 86400, db: Session = Depends(get_db),current_user = Depends(get_me)):
    org = db.query(Orga).filter(Orga.id == org_id, Orga.user_id == current_user.id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found or access denied")

    qr_service = QrService()
    result = qr_service.create_qr(db, org_id, expires_in)

    return QrCodeResponse(**result)


@orga.get("/join/{token}")
async def join_by_qr(token: str, db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    qr = db.query(QrCode).filter(QrCode.token == token, QrCode.is_active == True, QrCode.expires_at  > datetime.now(timezone.utc) ).first()
    if not qr:
        raise HTTPException(status_code=410, detail="QR code expired or invalid")
    org = db.query(Orga).filter(Orga.id == qr.organization_id).first()
    return {
        "organization": {
            "id": str(org.id),
            "name": org.legalName,
            "inn": org.inn
        },
        "action": "connect",
        "message": f"{current_user.fullName} connect to organization "
    }