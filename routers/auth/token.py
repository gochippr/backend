import logging
import uuid
from datetime import datetime, timedelta

import httpx
import jwt
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

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
    samesite="lax" if IS_DEV else "strict",
)

REFRESH_COOKIE_OPTIONS = CookieOptions(
    max_age=REFRESH_TOKEN_EXPIRY,
    path="/",
    httponly=True,
    secure=True if not IS_DEV else False,
    samesite="lax" if IS_DEV else "strict",
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

    # Remove Google-specific fields and exp from user info for our custom tokens
    # Keep only the user data we need
    user_data = {
        "sub": user_info.get("sub"),
        "name": user_info.get("name"),
        "email": user_info.get("email"),
        "picture": user_info.get("picture"),
        "given_name": user_info.get("given_name"),
        "family_name": user_info.get("family_name"),
        "email_verified": user_info.get("email_verified"),
    }

    # Get user subject (ID)
    sub = user_data.get("sub")
    if not sub:
        raise HTTPException(status_code=400, detail="Missing user subject")

    # Current timestamp
    issued_at = datetime.utcnow()

    # Generate unique JWT ID for refresh token
    jti = str(uuid.uuid4())

    # Create access token (short-lived) with our custom audience
    access_token_payload = {
        **user_data,
        "iat": issued_at,
        "exp": issued_at + timedelta(seconds=JWT_EXPIRATION_TIME),
        "aud": "chippr-app",  # Our custom audience
        "iss": "chippr-backend",  # Our custom issuer
    }

    access_token = jwt.encode(access_token_payload, JWT_SECRET, algorithm="HS256")
    logger.info(f"Created custom access token with payload: {access_token_payload}")
    logger.info(f"Access token length: {len(access_token)}")

    # Create refresh token (long-lived) with our custom audience and issuer
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
        "aud": "chippr-app",  # Our custom audience
        "iss": "chippr-backend",  # Our custom issuer
    }

    refresh_token = jwt.encode(refresh_token_payload, JWT_SECRET, algorithm="HS256")

    # Handle web platform with cookies
    if platform == "web":
        logger.info(
            f"Setting cookies for web platform. User: {user_info.get('name', 'Unknown')}"
        )
        logger.info(
            f"Cookie options - secure: {COOKIE_OPTIONS.secure}, samesite: {COOKIE_OPTIONS.samesite}"
        )

        response_data = {
            "success": True,
            "issuedAt": int(issued_at.timestamp()),
            "expiresAt": int(issued_at.timestamp()) + COOKIE_MAX_AGE,
        }

        response = JSONResponse(content=response_data)

        # Clear old cookies first to avoid conflicts
        logger.info("Clearing old cookies to avoid conflicts")
        response.set_cookie(
            key="access_token",
            value="",
            max_age=0,
            path="/",
            httponly=True,
            secure=COOKIE_OPTIONS.secure,
            samesite=COOKIE_OPTIONS.samesite,
            domain=None if IS_DEV else None,
        )
        response.set_cookie(
            key="refresh_token",
            value="",
            max_age=0,
            path="/",
            httponly=True,
            secure=COOKIE_OPTIONS.secure,
            samesite=COOKIE_OPTIONS.samesite,
            domain=None if IS_DEV else None,
        )

        # Set access token cookie
        logger.info(f"Setting access token cookie: {COOKIE_NAME}")
        logger.info(f"Access token value (first 50 chars): {access_token[:50]}...")
        response.set_cookie(
            key=COOKIE_NAME,
            value=access_token,
            max_age=COOKIE_OPTIONS.max_age,
            path=COOKIE_OPTIONS.path,
            httponly=COOKIE_OPTIONS.httponly,
            secure=COOKIE_OPTIONS.secure,
            samesite=COOKIE_OPTIONS.samesite,
            domain=None if IS_DEV else None,  # Allow cross-subdomain in dev
        )

        # Set refresh token cookie
        logger.info(f"Setting refresh token cookie: {REFRESH_COOKIE_NAME}")
        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value=refresh_token,
            max_age=REFRESH_COOKIE_OPTIONS.max_age,
            path=REFRESH_COOKIE_OPTIONS.path,
            httponly=REFRESH_COOKIE_OPTIONS.httponly,
            secure=REFRESH_COOKIE_OPTIONS.secure,
            samesite=REFRESH_COOKIE_OPTIONS.samesite,
            domain=None if IS_DEV else None,  # Allow cross-subdomain in dev
        )

        logger.info("Cookies set successfully for web platform")
        return response

    # For native platforms, return tokens in response body
    return {"accessToken": access_token, "refreshToken": refresh_token}
