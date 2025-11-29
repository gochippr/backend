import logging
import time
from typing import Dict, Optional

import jwt
from fastapi import APIRouter, HTTPException, Request
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from utils.constants import COOKIE_NAME, JWT_SECRET

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/session")


def parse_cookies_with_attributes(cookie_header: str) -> Dict[str, Dict[str, str]]:
    """
    Parse cookie header string into a dictionary with cookie values and attributes
    """
    cookies: Dict[str, Dict[str, str]] = {}

    if not cookie_header:
        return cookies

    cookie_parts = cookie_header.split(";")

    for cookie_part in cookie_parts:
        trimmed_cookie = cookie_part.strip()

        # Check if this is a cookie-value pair or an attribute
        if "=" in trimmed_cookie:
            key, value = trimmed_cookie.split("=", 1)
            cookie_name = key.strip()

            # Initialize the cookie entry if it doesn't exist
            if cookie_name not in cookies:
                cookies[cookie_name] = {"value": value}
            else:
                cookies[cookie_name]["value"] = value
        elif trimmed_cookie.lower() == "httponly":
            # Handle HttpOnly attribute
            if cookies:
                last_cookie_name = list(cookies.keys())[-1]
                cookies[last_cookie_name]["httpOnly"] = "true"
        elif trimmed_cookie.lower().startswith("expires="):
            # Handle Expires attribute
            if cookies:
                last_cookie_name = list(cookies.keys())[-1]
                cookies[last_cookie_name]["expires"] = trimmed_cookie[8:]
        elif trimmed_cookie.lower().startswith("max-age="):
            # Handle Max-Age attribute
            if cookies:
                last_cookie_name = list(cookies.keys())[-1]
                cookies[last_cookie_name]["maxAge"] = trimmed_cookie[8:]

    return cookies


@router.get("")
async def get_session(request: Request):
    """
    Session verification endpoint

    This endpoint verifies the user's authentication token from cookies
    and returns the user data along with cookie expiration information.
    """
    try:
        # Get the cookie from the request
        cookie_header = request.headers.get("cookie")
        logger.info(f"Session endpoint called - Cookie header: {cookie_header}")

        if not cookie_header:
            logger.warning("No cookie header found in request")
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Parse cookies and their attributes
        cookies = parse_cookies_with_attributes(cookie_header)
        logger.info(f"Parsed cookies: {cookies}")

        # Get the auth token from cookies - try new cookie name first, then fallback to old
        token = None
        cookie_used = None

        if COOKIE_NAME in cookies and cookies[COOKIE_NAME].get("value"):
            token = cookies[COOKIE_NAME]["value"]
            cookie_used = COOKIE_NAME
            logger.info(f"Using new cookie: {COOKIE_NAME}")
        elif "access_token" in cookies and cookies["access_token"].get("value"):
            token = cookies["access_token"]["value"]
            cookie_used = "access_token"
            logger.info("Using old access_token cookie (transition period)")
        else:
            logger.warning(
                f"Cookie '{COOKIE_NAME}' not found in cookies: {list(cookies.keys())}"
            )
            raise HTTPException(status_code=401, detail="Not authenticated")
        logger.info(f"Found token, length: {len(token)}")

        try:
            # First, let's decode without verification to see what's in the token
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            logger.info(f"Token payload (unverified): {unverified_payload}")

            # Verify the token with our custom audience and issuer
            logger.info("Attempting to decode JWT token...")
            verified = jwt.decode(
                token, 
                JWT_SECRET, 
                algorithms=["HS256"],
                audience="chippr-app",  # Verify our custom audience
                issuer="chippr-backend"  # Verify our custom issuer
            )
            logger.info(
                f"Token verified successfully. User: {verified.get('name', 'Unknown')}"
            )

            # Calculate cookie expiration time
            cookie_expiration: Optional[int] = None

            # If we have Max-Age, use it to calculate expiration
            if cookies[COOKIE_NAME].get("maxAge"):
                try:
                    max_age = int(cookies[COOKIE_NAME]["maxAge"])
                    # Calculate when the cookie will expire based on Max-Age
                    # We don't know exactly when it was set, but we can estimate
                    # using the token's iat (issued at) claim if available
                    issued_at = verified.get("iat", int(time.time()))
                    cookie_expiration = issued_at + max_age
                    logger.info(f"Cookie expiration calculated: {cookie_expiration}")
                except (ValueError, TypeError):
                    # If max_age is not a valid integer, skip expiration calculation
                    logger.warning(
                        f"Invalid max_age value: {cookies[COOKIE_NAME].get('maxAge')}"
                    )
                    pass

            # Return the user data from the token payload along with expiration info
            response_data = {**verified, "cookieExpiration": cookie_expiration}
            logger.info(
                f"Session verification successful for user: {response_data.get('name', 'Unknown')}"
            )

            return response_data

        except ExpiredSignatureError:
            # Token is expired
            logger.error("Token is expired")
            raise HTTPException(status_code=401, detail="Invalid token")
        except InvalidTokenError as e:
            # Token is invalid
            logger.error(f"Invalid token error: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as error:
        logger.error(f"Session error: {error}")
        raise HTTPException(status_code=500, detail="Server error")
