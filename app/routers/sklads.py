from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.core.core import get_db
from app.core.security import get_me
from app.models.auth import User
from app.models.orga import Orga
from app.models.sklads import SkladsCreate, SkladsUpdate, SkladsResponse
from app.services.sklads import SkladService

sklad = APIRouter(prefix="/api/sklads", tags=["Sklads"])


def req_found(
    current_user: User = Depends(get_me),
    db: Session = Depends(get_db)
):
    if current_user.role != "Founder":
        raise HTTPException(
            status_code=403,
            detail="only founder can access sklads"
        )

    if not current_user.connect_organization:
        raise HTTPException(
            status_code=403,
            detail="Сначала подключитесь к организации"
        )

    org = db.query(Orga).filter(
        Orga.id == UUID(current_user.connect_organization),
        Orga.user_id == current_user.id
    ).first()

    if not org:
        raise HTTPException(
            status_code=403,
            detail="you arent founder of this organisation"
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
async def get_sklads(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_me),
    db: Session = Depends(get_db)
):
    if not current_user.connect_organization:
        raise HTTPException(status_code=403, detail="Сначала подключитесь к организации")

    service = SkladService(db)
    return service.get_sklads(UUID(current_user.connect_organization), skip, limit)


@sklad.get("/{sklad_id}", response_model=SkladsResponse)
async def get_sklad(
    sklad_id: UUID,
    current_user: User = Depends(get_me),
    db: Session = Depends(get_db)
):
    if not current_user.connect_organization:
        raise HTTPException(status_code=403, detail="Сначала подключитесь к организации")

    service = SkladService(db)
    return service.get_sklad_by_id(sklad_id, UUID(current_user.connect_organization))


@sklad.patch("/{sklad_id}", response_model=SkladsResponse)
async def update_sklad(
    sklad_id: UUID,
    data: SkladsUpdate,
    deps: tuple = Depends(req_found),
    db: Session = Depends(get_db)
):
    current_user, org_id = deps
    service = SkladService(db)
    return service.update_sklad(sklad_id, data, org_id)


@sklad.delete("/{sklad_id}")
async def delete_sklad(
    sklad_id: UUID,
    deps: tuple = Depends(req_found),
    db: Session = Depends(get_db)
):
    current_user, org_id = deps
    service = SkladService(db)
    return service.delete_sklad(sklad_id, org_id)