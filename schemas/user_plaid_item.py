from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserPlaidItemCreate(BaseModel):
    user_id: str
    item_id: str
    access_token_encrypted: str
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None

class UserPlaidItemUpdate(BaseModel):
    access_token_encrypted: Optional[str] = None
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None
    cursor: Optional[str] = None
    is_active: Optional[bool] = None
    last_sync: Optional[datetime] = None

class UserPlaidItemResponse(BaseModel):
    id: int
    user_id: str
    item_id: str
    institution_id: Optional[str]
    institution_name: Optional[str]
    cursor: Optional[str]
    is_active: bool
    last_sync: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True