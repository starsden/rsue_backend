from app.models.orga import Orga, OrgaCreate, OrgaResponse
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from uuid import UUID

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
    db.commit()
    db.refresh(db_org)

    return OrgaResponse.from_orm(db_org)


