from app.models.orga import Orga, OrgaCreate, OrgaResponse, QrCode
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from uuid import UUID
from app.models.auth import User
from datetime import datetime, timezone
from app.core.security import verify_password


def cr_orga(db: Session, org_data: OrgaCreate, user_id: UUID) -> OrgaResponse:
    existing = db.query(Orga).filter(Orga.inn == org_data.inn).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="inn already exists",
        )

    db_org = Orga(
        user_id=user_id,
        legalName=org_data.legalName,
        description=org_data.description,
        inn=org_data.inn,
        address=org_data.address.dict(),
        settings=org_data.settings.dict()
    )

    db.add(db_org)
    db.flush()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Otter did not find such a user!")
    user.connect_organization = str(db_org.id)
    db.commit()
    db.refresh(db_org)

    return OrgaResponse.from_orm(db_org)


def del_orga(db: Session,org_id: UUID, user_id: UUID, password: str) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role != "Founder":
        raise HTTPException(
            status_code=403,
            detail="Only Founder can delete organization"
        )

    if not verify_password(password, user.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect password. The otter won't let you in."
        )

    org = db.query(Orga).filter(
        Orga.id == org_id,
        Orga.user_id == user_id,
        Orga.is_deleted == False
    ).first()

    if not org:
        raise HTTPException(
            status_code=404,
            detail="Organization not found or you are not the owner"
        )

    db.query(QrCode).filter(
        QrCode.organization_id == org_id,
        QrCode.is_active == True
    ).update({"is_active": False}, synchronize_session=False)

    db.query(User).filter(
        User.connect_organization == str(org_id)
    ).update({
        "connect_organization": None,
        "choosen_sklad": None
    }, synchronize_session=False)

    org.is_deleted = True
    org.deleted_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "message": f"Organization '{org.legalName}' has been deleted.",
        "org_id": str(org_id),
        "deleted_at": org.deleted_at.isoformat()
    }