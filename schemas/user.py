from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    id: str  # Google sub
    email: EmailStr
    name: str
    picture: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    email_verified: Optional[bool] = False
    provider: Optional[str] = "google"


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    email_verified: Optional[bool] = None
    provider: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str]
    given_name: Optional[str]
    family_name: Optional[str]
    email_verified: bool
    provider: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True 