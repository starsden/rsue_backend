from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.core import get_db
from app.core.security import get_me
from app.services.orga_service import cr_orga
from app.models.orga import OrgaCreate, OrgaResponse
from app.models.auth import User

orga = APIRouter(prefix="/api/orga", tags=["organisation"])
@orga.post("/create", response_model=OrgaResponse, status_code=status.HTTP_201_CREATED, summary="Создать организацию (требуется авторизация)")
async def create_orga(org_data: OrgaCreate, db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    return cr_orga(db, org_data, user_id=current_user.id)