from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.core.core import get_db
from app.core.security import get_me
from app.models.auth import User, ChooseSkladRequest, ChooseSkladResponse
from app.models.orga import Orga
from app.models.sklads import SkladsCreate, SkladsUpdate, SkladsResponse, Sklads
from app.services.sklads import SkladService

sklad = APIRouter(prefix="/api/sklads", tags=["Sklads"])


def req_found(current_user: User = Depends(get_me), db: Session = Depends(get_db)):
    if current_user.role != "Founder":
        raise HTTPException(
            status_code=403,
            detail="only founder can access sklads"
        )

    if not current_user.connect_organization:
        raise HTTPException(
            status_code=403,
            detail="Firstly, get involved in the organization, and secondly, don't mess with the otter!"
        )

    org = db.query(Orga).filter(
        Orga.id == UUID(current_user.connect_organization),
        Orga.user_id == current_user.id
    ).first()

    if not org:
        raise HTTPException(
            status_code=403,
            detail="you arent founder of this organisation( "
        )

    return current_user, UUID(current_user.connect_organization)


@sklad.post("/", response_model=SkladsResponse, status_code=status.HTTP_201_CREATED)
async def create_sklad(
    data: SkladsCreate,
    deps: tuple = Depends(req_found),
    db: Session = Depends(get_db)
):
    current_user, org_id = deps
    service = SkladService(db)
    return service.create_sklad(data, org_id)


@sklad.get("/", response_model=List[SkladsResponse])
async def get_sklads(skip: int = 0, limit: int = 100, deps: tuple = Depends(req_found), db: Session = Depends(get_db)):
    current_user, org_id = deps
    service = SkladService(db)
    sklads = service.get_sklads(org_id, skip=skip, limit=limit)
    return sklads

@sklad.get("/{sklad_id}", response_model=SkladsResponse)
async def get_sklad(sklad_id: UUID, current_user: User = Depends(get_me), db: Session = Depends(get_db)):
    if not current_user.connect_organization:
        raise HTTPException(status_code=403, detail="Firstly, get involved in the organization, and secondly, don't mess with the otter!")

    service = SkladService(db)
    return service.get_sklad_by_id(sklad_id, UUID(current_user.connect_organization))


@sklad.patch("/{sklad_id}", response_model=SkladsResponse)
async def update_sklad(sklad_id: UUID, data: SkladsUpdate, deps: tuple = Depends(req_found), db: Session = Depends(get_db)):
    current_user, org_id = deps
    service = SkladService(db)
    return service.update_sklad(sklad_id, data, org_id)


@sklad.delete("/{sklad_id}")
async def delete_sklad(sklad_id: UUID, deps: tuple = Depends(req_found), db: Session = Depends(get_db)):
    current_user, org_id = deps
    service = SkladService(db)
    return service.delete_sklad(sklad_id, org_id)



@sklad.post("/choose", response_model=ChooseSkladResponse,summary="Выбрать текущий склад для работы")
async def choose_sklad(request: ChooseSkladRequest, db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    if not current_user.connect_organization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any organization"
        )

    sklad = db.query(Sklads).filter(
        Sklads.id == request.sklad_id,
        Sklads.organization_id == current_user.connect_organization,
        Sklads.is_deleted == False
    ).first()

    if not sklad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found or does not belong to your organization"
        )

    current_user.choosen_sklad = request.sklad_id
    db.commit()
    db.refresh(current_user)

    return ChooseSkladResponse(
        message="Склад успешно выбран",
        choosen_sklad=request.sklad_id
    )
