from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class FriendUser(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str]
    photo_url: Optional[str]


class FriendRelationship(BaseModel):
    friend: FriendUser
    status: str
    initiator_user_id: str
    created_at: datetime
    updated_at: datetime
    is_incoming_request: bool
    is_outgoing_request: bool


class FriendListResponse(BaseModel):
    friends: List[FriendRelationship]


class FriendRequestListResponse(BaseModel):
    incoming: List[FriendRelationship]
    outgoing: List[FriendRelationship]


class FriendRequestCreate(BaseModel):
    email: EmailStr
