from dataclasses import dataclass
from typing import Literal


@dataclass
class CookieOptions:
    max_age: int
    path: str
    httponly: bool
    secure: bool
    samesite: Literal["lax", "strict", "none"]
