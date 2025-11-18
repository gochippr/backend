from dataclasses import dataclass
from typing import Optional


@dataclass
class AuthUser:
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    email_verified: Optional[bool] = None
    provider: Optional[str] = None
    exp: Optional[int] = None
    cookie_expiration: Optional[int] = None
