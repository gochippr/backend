from typing import Dict, List, Optional

import jwt
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware

from models.auth_user import AuthUser
from utils.constants import COOKIE_NAME, JWT_SECRET


def parse_cookies(cookie_header: str) -> Dict[str, str]:
    """Parse cookie header string into a dictionary"""
    cookies = {}
    if cookie_header:
        for cookie in cookie_header.split(";"):
            if "=" in cookie:
                key, value = cookie.strip().split("=", 1)
                cookies[key.strip()] = value
    return cookies


def extract_token_from_request(request: Request) -> Optional[str]:
    """Extract JWT token from Authorization header or cookies"""
    token = None

    # First, try to get token from Authorization header (for native apps)
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

    # If no token in header, try to get from cookies (for web)
    if not token:
        cookie_header = request.headers.get("cookie")
        if cookie_header:
            cookies = parse_cookies(cookie_header)
            token = cookies.get(COOKIE_NAME)

    return token


def verify_token(token: str) -> AuthUser:
    """Verify JWT token and return user data"""
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    try:
        # Verify and decode the token with audience and issuer verification
        decoded = jwt.decode(
            token, 
            JWT_SECRET, 
            algorithms=["HS256"],
            audience="chippr-app",  # Verify our custom audience
            issuer="chippr-backend"  # Verify our custom issuer
        )

        # Create AuthUser from decoded payload
        user = AuthUser(
            id=decoded.get("sub", ""),
            email=decoded.get("email", ""),
            name=decoded.get("name", ""),
            picture=decoded.get("picture"),
            given_name=decoded.get("given_name"),
            family_name=decoded.get("family_name"),
            email_verified=decoded.get("email_verified"),
            provider=decoded.get("provider"),
            exp=decoded.get("exp"),
            cookie_expiration=decoded.get("cookieExpiration"),
        )

        return user

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Dependency function for route-level authentication
def get_current_user(request: Request) -> AuthUser:
    """Dependency to get current authenticated user"""
    token = extract_token_from_request(request)

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    return verify_token(token)


# Optional: Dependency that doesn't raise an exception if no auth
def get_current_user_optional(request: Request) -> Optional[AuthUser]:
    """Optional dependency to get current user (returns None if not authenticated)"""
    token = extract_token_from_request(request)

    if not token:
        return None

    try:
        return verify_token(token)
    except HTTPException:
        return None
