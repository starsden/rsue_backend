from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.core import get_db
from app.core.security import get_me
from app.services.orga_service import cr_orga, del_orga, upd_orga
from app.services.qr_service import QrService
from app.models.orga import OrgaCreate, OrgaResponse, QrCodeResponse, QrCode, Orga, UserInOrgaResp, MyOrga, UsersInOrg, DeleteOrga, OrgaUpdate
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


@orga.get("/{org_id}/members", response_model=List[UserInOrgaResp], tags=["Organisation"])
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

    return [UserInOrgaResp.from_orm(m) for m in members]


@orga.get("/me", response_model=MyOrga, tags=["Organisation"])
async def get_my_org(current_user: User = Depends(get_me), db: Session = Depends(get_db)):
    if not current_user.connect_organization:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of the organization. Join us using a QR code")

    try:
        org_id = UUID(current_user.connect_organization)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="uncorrect org_id"
        )

    org = db.query(Orga).filter(Orga.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="org not found"
        )

    members = db.query(User).filter(
        User.connect_organization == str(org_id)
    ).all()

    members_count = len(members)
    members_list = [
        UsersInOrg.from_orm(user) for user in members
    ]

    return MyOrga(
        id=org.id,
        name=getattr(org, 'name', org.legalName),
        legalName=org.legalName,
        description=org.description,
        inn=org.inn,
        address=org.address,
        settings=org.settings,
        members_count=members_count,
        members=members_list
    )


@orga.delete("/{org_id}", response_model=dict, status_code=status.HTTP_200_OK, summary="Удалить организацию (с подтверждением паролем)", tags=["Organisation"])
async def delete_orga(org_id: UUID, request: DeleteOrga, db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    return del_orga(db=db, org_id=org_id, user_id=current_user.id, password=request.password)

@orga.patch("/upd/{org_id}", response_model=dict, status_code=status.HTTP_200_OK, summary="Обновить организацию", tags=["Organisation"])
async def update_organization_endpoint(org_id: UUID, update_data: OrgaUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    return upd_orga(db=db, org_id=org_id, user_id=current_user.id, update_data=update_data)
