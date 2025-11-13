from datetime import datetime
from typing import List, Literal
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.orga import InvitationResponse


class UserLookupItem(BaseModel):
    id: UUID
    full_name: str
    email: str
    phone: str | None = None
    role: str | None = None
    connect_organization: str | None = None

    class Config:
        from_attributes = True


class UserSearchResponse(BaseModel):
    results: List[UserLookupItem]

class UserDashboardResponse(BaseModel):
    id: UUID
    full_name: str = Field(alias="fullName")
    email: str
    phone: str | None = None
    role: str | None = None
    connect_organization: str | None = None
    invitations: List[InvitationResponse]

    class Config:
        from_attributes = True
        populate_by_name = True
class CurrentUserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    choosen_sklad: UUID | None = None
    invitations: List[InvitationResponse]


class InvitationActionRequest(BaseModel):
    action: Literal["accept", "decline"]


class InvitationActionResponse(BaseModel):
    invitation_id: UUID
    status: Literal["accepted", "declined", "cancelled"]
    message: str
    responded_at: datetime | None = None

