from fastapi import APIRouter, Depends

from models.auth_user import AuthUser
from utils.middlewares.auth_user import get_current_user

router = APIRouter(prefix="/protected")


@router.get("")
async def protected_route(current_user: AuthUser = Depends(get_current_user)):
    """
    Protected route that requires authentication.

    This route can only be accessed by authenticated users.
    """
    return {"message": "This is a protected route", "user": current_user.name}
