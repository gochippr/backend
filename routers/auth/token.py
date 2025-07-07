import uuid
from datetime import datetime, timedelta

import httpx
import jwt
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse

from models.cookies import CookieOptions
from utils.constants import (
    API_URL,
    COOKIE_MAX_AGE,
    COOKIE_NAME,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    IS_DEV,
    JWT_EXPIRATION_TIME,
    JWT_SECRET,
    REFRESH_COOKIE_NAME,
    REFRESH_TOKEN_EXPIRY,
)

COOKIE_OPTIONS = CookieOptions(
    max_age=COOKIE_MAX_AGE,
    path="/",
    httponly=True,
    secure=True if not IS_DEV else False,
    samesite="strict",
)

REFRESH_COOKIE_OPTIONS = CookieOptions(
    max_age=REFRESH_TOKEN_EXPIRY,
    path="/",
    httponly=True,
    secure=True if not IS_DEV else False,
    samesite="strict",
)

router = APIRouter(prefix="/token")


@router.post("")
async def oauth_callback(code: str = Form(...), platform: str = Form(default="native")):
    """
    Handle exchange authorization code for tokens
    """

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Exchange authorization code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": f"{API_URL}/auth/callback",
                "grant_type": "authorization_code",
                "code": code,
            },
        )

    token_data = token_response.json()

    if "error" in token_data:
        raise HTTPException(
            status_code=400,
            detail={
                "error": token_data.get("error"),
                "error_description": token_data.get("error_description"),
                "message": "OAuth validation error - please ensure the app complies with Google's OAuth 2.0 policy",
            },
        )

    if not token_data.get("id_token"):
        raise HTTPException(status_code=400, detail="Missing required parameters")

    # Decode the ID token to get user info
    try:
        user_info = jwt.decode(
            token_data["id_token"],
            options={"verify_signature": False},  # Google's token is already verified
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid ID token")

    # Remove exp from user info for our custom tokens
    user_info_without_exp = {k: v for k, v in user_info.items() if k != "exp"}

    # Get user subject (ID)
    sub = user_info.get("sub")
    if not sub:
        raise HTTPException(status_code=400, detail="Missing user subject")

    # Current timestamp
    issued_at = datetime.utcnow()

    # Generate unique JWT ID for refresh token
    jti = str(uuid.uuid4())

    # Create access token (short-lived)
    access_token_payload = {
        **user_info_without_exp,
        "sub": sub,
        "iat": issued_at,
        "exp": issued_at + timedelta(seconds=JWT_EXPIRATION_TIME),
    }

    access_token = jwt.encode(access_token_payload, JWT_SECRET, algorithm="HS256")

    # Create refresh token (long-lived)
    refresh_token_payload = {
        "sub": sub,
        "jti": jti,
        "type": "refresh",
        "name": user_info.get("name"),
        "email": user_info.get("email"),
        "picture": user_info.get("picture"),
        "given_name": user_info.get("given_name"),
        "family_name": user_info.get("family_name"),
        "email_verified": user_info.get("email_verified"),
        "iat": issued_at,
        "exp": issued_at + timedelta(seconds=REFRESH_TOKEN_EXPIRY),
    }

    refresh_token = jwt.encode(refresh_token_payload, JWT_SECRET, algorithm="HS256")

    # Handle web platform with cookies
    if platform == "web":
        response_data = {
            "success": True,
            "issuedAt": int(issued_at.timestamp()),
            "expiresAt": int(issued_at.timestamp()) + COOKIE_MAX_AGE,
        }

        response = JSONResponse(content=response_data)

        # Set access token cookie
        response.set_cookie(
            key=COOKIE_NAME,
            value=access_token,
            max_age=COOKIE_OPTIONS.max_age,
            path=COOKIE_OPTIONS.path,
            httponly=COOKIE_OPTIONS.httponly,
            secure=COOKIE_OPTIONS.secure,
            samesite=COOKIE_OPTIONS.samesite,
        )

        # Set refresh token cookie
        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value=refresh_token,
            max_age=REFRESH_COOKIE_OPTIONS.max_age,
            path=REFRESH_COOKIE_OPTIONS.path,
            httponly=REFRESH_COOKIE_OPTIONS.httponly,
            secure=REFRESH_COOKIE_OPTIONS.secure,
            samesite=REFRESH_COOKIE_OPTIONS.samesite,
        )

        return response

    # For native platforms, return tokens in response body
    return {"accessToken": access_token, "refreshToken": refresh_token}
