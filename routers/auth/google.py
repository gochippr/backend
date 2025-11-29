from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from utils.constants import (
    API_URL,
    APP_SCHEME,
    GOOGLE_AUTH_URL,
    GOOGLE_CLIENT_ID,
)

router = APIRouter(prefix="/authorize/google")


@router.get("")
async def google_auth(
    request: Request,
    client_id: str = Query(..., description="Internal client identifier"),
    redirect_uri: str = Query(..., description="Redirect URI after auth"),
    state: Optional[str] = Query(
        None, description="State parameter for CSRF protection"
    ),
    scope: Optional[str] = Query("identity", description="OAuth scope"),
):
    """Initiate Google OAuth authentication flow"""

    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500, detail="Missing GOOGLE_CLIENT_ID environment variable"
        )

    if redirect_uri == APP_SCHEME:
        platform = "mobile"
    else:
        platform = "web"

    combined_state = f"{platform}|{state}" if state else platform

    if client_id != "google":
        raise HTTPException(status_code=400, detail="Invalid client")

    if not combined_state:
        raise HTTPException(status_code=400, detail="Invalid state")

    oauth_params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": f"{API_URL}/auth/callback",
        "response_type": "code",
        "scope": scope,
        "state": combined_state,
        "prompt": "select_account",
    }
    print(f"Redirecting to Google OAuth with params: {oauth_params}")

    # Create the Google OAuth URL
    google_oauth_url = f"{GOOGLE_AUTH_URL}?{urlencode(oauth_params)}"
    return RedirectResponse(url=google_oauth_url)
