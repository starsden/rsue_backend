from fastapi import APIRouter, Depends, Query, Path, Body, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.core import get_db
from app.core.security import get_me
from app.models.nomen import NomenclatureCreate, NomenclatureUpdate, NomenclatureResponse
from app.models.auth import User
from app.services.nomen_service import NomenclatureService

nomen = APIRouter(prefix="/api/reestr", tags=["Nomenclature"])
h = ["Are you okey?"]
@nomen.post("/create", response_model=NomenclatureResponse, status_code=status.HTTP_201_CREATED)
def cr_nomen(data: NomenclatureCreate = Body(...), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = NomenclatureService(db)
    return service.create_nomen(data, current_user)
@nomen.get("/list", response_model=List[NomenclatureResponse])
def list_nomen(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1), search: str = Query(None), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = NomenclatureService(db)
    return service.get_nomen(
        skip=skip,
        limit=limit,
        search=search,
        current_user=current_user
    )
@nomen.get("/get/{item_id}", response_model=NomenclatureResponse)
def get_nomen(item_id: UUID = Path(...), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = NomenclatureService(db)
    return service.get_nomen_by_id(item_id, current_user=current_user)


@nomen.put("/upd/{item_id}", response_model=NomenclatureResponse)
def upd_nomen(item_id: UUID = Path(...), data: NomenclatureUpdate = Body(...), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = NomenclatureService(db)
    return service.upd_nomen(item_id, data, current_user=current_user)


@nomen.delete("/del/{item_id}", status_code=status.HTTP_200_OK)
def del_nomen(item_id: UUID = Path(...), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = NomenclatureService(db)
    return service.del_nomen(item_id, current_user=current_user)


@nomen.get("/search", response_model=List[NomenclatureResponse], summary="Поиск по штрихкоду")
def search(barcode: str = Query(..., min_length=8), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = NomenclatureService(db)
    return service.search(barcode, current_user=current_user)

@nomen.post("/health", tags=h)
async def health():
    return {"status": "otter said: i'm okey! thank u <3"}