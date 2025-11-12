from fastapi import APIRouter, Depends, Query, Header, Body, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.core.core import get_db
from app.core.security import get_me
from app.core.api_keys import validate_key
from app.models.auth import User
from app.models.offline import OfflineTokenCreate, OfflineTokenResponse
from app.services.offline_service import OfflineService


offline = APIRouter(prefix="/api/offline", tags=["Offline Access"])


@offline.post("/sklad/{sklad_id}/token", response_model=OfflineTokenResponse, status_code=status.HTTP_201_CREATED)
def create_token(sklad_id: UUID, payload: OfflineTokenCreate = Body(...), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    if current_user.role != "Founder":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Founder can create offline tokens")
    service = OfflineService(db)
    return service.create_token(sklad_id, payload, current_user)


@offline.get("/sklad")
def get_offline(token: str = Query(...), device_id: str = Query(...), x_api_key: Optional[str] = Header(None, alias="X-API-Key"), db: Session = Depends(get_db)):
    if not x_api_key or not validate_key(x_api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
    service = OfflineService(db)
    return service.get_sklad_data(token, device_id)

