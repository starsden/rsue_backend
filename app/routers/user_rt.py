from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.core import get_db
from app.core.security import get_me
from app.models.auth import User
from app.models.user_profile import InvitationActionRequest, InvitationActionResponse, UserDashboardResponse, UserSearchResponse
from app.services.invitation_service import get_user, respond_to_invite, search_by_parameter


user = APIRouter(prefix="/api/users", tags=["Users"])


@user.get("/search", response_model=UserSearchResponse)
async def find_user(org_id: UUID, email: str | None = None, phone: str | None = None, full_name: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_me)) -> UserSearchResponse:
    return search_by_parameter(db, current_user=current_user, org_id=org_id, email=email, phone=phone, full_name=full_name)


@user.get("/me/dashboard", response_model=UserDashboardResponse)
async def get_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_me)) -> UserDashboardResponse:
    return get_user(db, current_user=current_user)


@user.post("/me/invitations/{invitation_id}", response_model=InvitationActionResponse)
async def handle_invitation(invitation_id: UUID, request: InvitationActionRequest, db: Session = Depends(get_db), current_user: User = Depends(get_me),) -> InvitationActionResponse:
    return respond_to_invite(db, invitation_id=invitation_id, current_user=current_user, action=request.action)

