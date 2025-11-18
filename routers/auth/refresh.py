import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

import jwt
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from database.supabase.users import get_user_by_id
from models.cookies import CookieOptions
from utils.constants import (
    COOKIE_MAX_AGE,
    COOKIE_NAME,
    IS_DEV,
    JWT_EXPIRATION_TIME,
    JWT_SECRET,
    REFRESH_COOKIE_NAME,
    REFRESH_TOKEN_EXPIRY,
)

logger = logging.getLogger(__name__)

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

router = APIRouter(prefix="/refresh")


def parse_cookies(cookie_header: str) -> Dict[str, str]:
    """Parse cookie header string into a dictionary"""
    cookies = {}
    if cookie_header:
        for cookie in cookie_header.split(";"):
            if "=" in cookie:
                key, value = cookie.strip().split("=", 1)
                cookies[key.strip()] = value
    return cookies


@router.post("")
async def refresh_token(request: Request):
    """
    Refresh API endpoint

    This endpoint refreshes the user's authentication token using a refresh token.
    It implements token rotation - each refresh generates a new refresh token.
    For web clients, it refreshes the cookies.
    For native clients, it returns new tokens.
    """
    try:
        # Determine the platform (web or native)
        platform = "native"
        refresh_token: Optional[str] = None

        # Check content type to determine how to parse the body
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            # Handle JSON body
            try:
                json_body = await request.json()
                platform = json_body.get("platform", "native")

                # For native clients, get refresh token from request body
                if platform == "native" and json_body.get("refreshToken"):
                    refresh_token = json_body["refreshToken"]
            except Exception as e:
                logger.warning(
                    f"Failed to parse JSON body, using default platform: {e}"
                )

        elif (
            "application/x-www-form-urlencoded" in content_type
            or "multipart/form-data" in content_type
        ):
            # Handle form data
            try:
                form_data = await request.form()
                platform = form_data.get("platform", "native")

                # For native clients, get refresh token from form data
                if platform == "native" and form_data.get("refreshToken"):
                    refresh_token = form_data["refreshToken"]
            except Exception as e:
                logger.warning(
                    f"Failed to parse form data, using default platform: {e}"
                )
        else:
            # For other content types or no content type, check URL parameters
            try:
                query_params = dict(request.query_params)
                platform = query_params.get("platform", "native")
            except Exception as e:
                logger.warning(
                    f"Failed to parse URL parameters, using default platform: {e}"
                )

        # For web clients, get refresh token from cookies
        if platform == "web" and not refresh_token:
            cookie_header = request.headers.get("cookie")
            if cookie_header:
                cookies = parse_cookies(cookie_header)
                refresh_token = cookies.get(REFRESH_COOKIE_NAME)

        # If no refresh token found, try to use the access token as fallback
        if not refresh_token:
            # For native clients, get access token from Authorization header
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                access_token = auth_header.split(" ")[1]

                try:
                    # Verify the access token
                    decoded = jwt.decode(access_token, JWT_SECRET, algorithms=["HS256"])

                    # If token is still valid, use it to create a new token
                    logger.warning(
                        "No refresh token found, using access token as fallback"
                    )

                    # Get the user info from the token
                    user_info = decoded

                    # Current timestamp
                    issued_at = datetime.utcnow()

                    # Create a new access token
                    new_access_token_payload = {
                        **user_info,
                        "iat": issued_at,
                        "exp": issued_at + timedelta(seconds=JWT_EXPIRATION_TIME),
                        "aud": "chippr-app",  # Our custom audience
                        "iss": "chippr-backend",  # Our custom issuer
                    }

                    new_access_token = jwt.encode(
                        new_access_token_payload, JWT_SECRET, algorithm="HS256"
                    )

                    # For web platform with cookies
                    if platform == "web":
                        response_data = {
                            "success": True,
                            "issuedAt": int(issued_at.timestamp()),
                            "expiresAt": int(issued_at.timestamp()) + COOKIE_MAX_AGE,
                            "warning": "Using access token fallback - refresh token missing",
                        }

                        response = JSONResponse(content=response_data)

                        response.set_cookie(
                            key=COOKIE_NAME,
                            value=new_access_token,
                            max_age=COOKIE_OPTIONS.max_age,
                            path=COOKIE_OPTIONS.path,
                            httponly=COOKIE_OPTIONS.httponly,
                            secure=COOKIE_OPTIONS.secure,
                            samesite=COOKIE_OPTIONS.samesite,
                            domain=None if IS_DEV else None,  # Allow cross-subdomain in dev
                        )

                        return response

                    # For native platforms
                    return {
                        "accessToken": new_access_token,
                        "warning": "Using access token fallback - refresh token missing",
                    }

                except (InvalidTokenError, ExpiredSignatureError):
                    # Access token is invalid or expired
                    raise HTTPException(
                        status_code=401,
                        detail="Authentication required - no valid refresh token",
                    )

            raise HTTPException(
                status_code=401, detail="Authentication required - no refresh token"
            )

        # Verify the refresh token
        try:
            decoded = jwt.decode(
                refresh_token, 
                JWT_SECRET, 
                algorithms=["HS256"],
                audience="chippr-app",  # Verify our custom audience
                issuer="chippr-backend"  # Verify our custom issuer
            )
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=401, detail="Refresh token expired, please sign in again"
            )
        except InvalidTokenError:
            raise HTTPException(
                status_code=401, detail="Invalid refresh token, please sign in again"
            )

        # Verify this is actually a refresh token
        payload = decoded
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=401, detail="Invalid token type, please sign in again"
            )

        # Get the subject (user ID) from the token
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=401, detail="Invalid token, missing subject"
            )

        # Current timestamp
        issued_at = datetime.utcnow()

        # Generate a unique jti (JWT ID) for the new refresh token
        jti = str(uuid.uuid4())

        # Get the user info from the token
        user_info = decoded

        # Check if we have all the required user information
        has_required_user_info = (
            user_info.get("name")
            and user_info.get("email")
            and user_info.get("picture")
        )

        # Create a complete user info object
        complete_user_info = dict(user_info)

        # If we're missing user info, fetch from database
        if not has_required_user_info:
            # Fetch the user data from database using the sub (user ID)
            db_user = get_user_by_id(sub)
            
            if db_user:
                # Update with database information
                complete_user_info.update(
                    {
                        "type": "refresh",  # Preserve the refresh token type
                        "name": db_user.get("name"),
                        "email": db_user.get("email"),
                        "picture": db_user.get("picture"),
                        "given_name": db_user.get("given_name"),
                        "family_name": db_user.get("family_name"),
                        "email_verified": db_user.get("email_verified"),
                    }
                )
            else:
                # User not found in database - this shouldn't happen
                logger.error(f"User not found in database: {sub}")
                raise HTTPException(
                    status_code=401, 
                    detail="User account not found, please sign in again"
                )

        # Create a new access token with complete user info
        access_token_info = {k: v for k, v in complete_user_info.items() if k != "type"}
        new_access_token_payload = {
            **access_token_info,
            "iat": issued_at,
            "exp": issued_at + timedelta(seconds=JWT_EXPIRATION_TIME),
            "aud": "chippr-app",  # Our custom audience
            "iss": "chippr-backend",  # Our custom issuer
        }

        new_access_token = jwt.encode(
            new_access_token_payload, JWT_SECRET, algorithm="HS256"
        )

        # Create a new refresh token (token rotation) with our custom audience and issuer
        new_refresh_token_payload = {
            **complete_user_info,
            "jti": jti,
            "type": "refresh",
            "iat": issued_at,
            "exp": issued_at + timedelta(seconds=REFRESH_TOKEN_EXPIRY),
            "aud": "chippr-app",  # Our custom audience
            "iss": "chippr-backend",  # Our custom issuer
        }

        new_refresh_token = jwt.encode(
            new_refresh_token_payload, JWT_SECRET, algorithm="HS256"
        )

        # Handle web platform with cookies
        if platform == "web":
            # Create a response with success info
            response_data = {
                "success": True,
                "issuedAt": int(issued_at.timestamp()),
                "expiresAt": int(issued_at.timestamp()) + COOKIE_MAX_AGE,
            }

            response = JSONResponse(content=response_data)

            # Set the new access token in an HTTP-only cookie
            response.set_cookie(
                key=COOKIE_NAME,
                value=new_access_token,
                max_age=COOKIE_OPTIONS.max_age,
                path=COOKIE_OPTIONS.path,
                httponly=COOKIE_OPTIONS.httponly,
                secure=COOKIE_OPTIONS.secure,
                samesite=COOKIE_OPTIONS.samesite,
                domain=None if IS_DEV else None,  # Allow cross-subdomain in dev
            )

            # Set the new refresh token in a separate HTTP-only cookie
            response.set_cookie(
                key=REFRESH_COOKIE_NAME,
                value=new_refresh_token,
                max_age=REFRESH_COOKIE_OPTIONS.max_age,
                path=REFRESH_COOKIE_OPTIONS.path,
                httponly=REFRESH_COOKIE_OPTIONS.httponly,
                secure=REFRESH_COOKIE_OPTIONS.secure,
                samesite=REFRESH_COOKIE_OPTIONS.samesite,
                domain=None if IS_DEV else None,  # Allow cross-subdomain in dev
            )

            return response

        # For native platforms, return the new tokens in the response body
        return {"accessToken": new_access_token, "refreshToken": new_refresh_token}

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as error:
        logger.error(f"Refresh token error: {error}")
        raise HTTPException(status_code=500, detail="Failed to refresh token")
