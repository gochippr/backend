from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from models.cookies import CookieOptions
from utils.constants import (
    COOKIE_NAME,
    REFRESH_COOKIE_NAME,
)

# You'll need to import or define these from your constants
# For now, I'm including typical values - adjust according to your constants
COOKIE_OPTIONS = CookieOptions(
    max_age=3600,  # This won't be used for logout, but needed for structure
    path="/",
    httponly=True,
    secure=True,  # Set based on your environment
    samesite="strict",
)

REFRESH_COOKIE_OPTIONS = CookieOptions(
    max_age=2592000,  # This won't be used for logout, but needed for structure
    path="/",
    httponly=True,
    secure=True,  # Set based on your environment
    samesite="strict",
)

router = APIRouter(prefix="/logout")


@router.post("")
async def logout():
    """
    Logout endpoint

    This endpoint clears the authentication cookies by setting them
    with Max-Age=0, effectively removing them from the client.
    """
    try:
        # Create a response with success message
        response_data = {"success": True}
        response = JSONResponse(content=response_data)

        # Clear the access token cookie by setting Max-Age=0
        response.set_cookie(
            key=COOKIE_NAME,
            value="",  # Empty value
            max_age=0,  # This expires the cookie immediately
            path=COOKIE_OPTIONS.path,
            httponly=COOKIE_OPTIONS.httponly,
            secure=COOKIE_OPTIONS.secure,
            samesite=COOKIE_OPTIONS.samesite,
        )

        # Clear the refresh token cookie by setting Max-Age=0
        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value="",  # Empty value
            max_age=0,  # This expires the cookie immediately
            path=REFRESH_COOKIE_OPTIONS.path,
            httponly=REFRESH_COOKIE_OPTIONS.httponly,
            secure=REFRESH_COOKIE_OPTIONS.secure,
            samesite=REFRESH_COOKIE_OPTIONS.samesite,
        )

        return response

    except Exception as error:
        print(f"Logout error: {error}")

        raise HTTPException(status_code=500, detail="Server error")
