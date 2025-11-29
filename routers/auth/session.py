import time
from typing import Dict, Optional

import jwt
from fastapi import APIRouter, HTTPException, Request
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from utils.constants import COOKIE_NAME, JWT_SECRET

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
        if not cookie_header:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Parse cookies and their attributes
        cookies = parse_cookies_with_attributes(cookie_header)

        # Get the auth token from cookies
        if COOKIE_NAME not in cookies or not cookies[COOKIE_NAME].get("value"):
            raise HTTPException(status_code=401, detail="Not authenticated")

        token = cookies[COOKIE_NAME]["value"]

        try:
            # Verify the token
            verified = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

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
                except (ValueError, TypeError):
                    # If max_age is not a valid integer, skip expiration calculation
                    pass

            # Return the user data from the token payload along with expiration info
            response_data = {**verified, "cookieExpiration": cookie_expiration}

            return response_data

        except ExpiredSignatureError:
            # Token is expired
            raise HTTPException(status_code=401, detail="Invalid token")
        except InvalidTokenError:
            # Token is invalid
            raise HTTPException(status_code=401, detail="Invalid token")

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as error:
        print(f"Session error: {error}")
        raise HTTPException(status_code=500, detail="Server error")
