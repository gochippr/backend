from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from utils.constants import (
    APP_SCHEME,
    WEBAPP_URL,
)

router = APIRouter(prefix="/auth/callback")


@router.get("/")
async def oauth_callback(
    request: Request,
    code: Optional[str] = Query(
        None, description="Authorization code from OAuth provider"
    ),
    state: Optional[str] = Query(
        None, description="Combined platform and state parameter"
    ),
    error: Optional[str] = Query(
        None, description="Error parameter from OAuth provider"
    ),
):
    """Handle OAuth callback from Google"""

    # Validate state parameter
    if not state:
        raise HTTPException(status_code=400, detail="Invalid state")

    # Parse platform and original state from combined state
    state_parts = state.split(
        "|", 1
    )  # Split only on first "|" to handle state with "|"
    platform = state_parts[0]
    original_state = state_parts[1] if len(state_parts) > 1 else ""

    # Determine redirect URL based on platform
    if platform == "web":
        redirect_base = WEBAPP_URL
    elif platform == "mobile":
        redirect_base = APP_SCHEME
    else:
        raise HTTPException(status_code=400, detail="Invalid platform in state")

    # Build outgoing parameters
    outgoing_params = {}

    # Add code if present
    if code:
        outgoing_params["code"] = code

    # Add original state if present
    if original_state:
        outgoing_params["state"] = original_state

    # Add error if present (OAuth provider returned an error)
    if error:
        outgoing_params["error"] = error

    # Construct final redirect URL
    if outgoing_params:
        redirect_url = f"{redirect_base}?{urlencode(outgoing_params)}"
    else:
        redirect_url = redirect_base

    return RedirectResponse(url=redirect_url)
