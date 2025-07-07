import os

from dotenv import load_dotenv

load_dotenv(".env.local")

# Google OAuth configuration
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# ENV variables
API_URL = os.getenv("API_URL", "http://localhost:8000")
APP_SCHEME = os.getenv("APP_SCHEME", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8081")
IS_DEV = os.getenv("IS_DEV", "true").lower() in ("true", "1", "yes")


# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "chippr_secret")
JWT_REFRESH_SECRET = os.getenv("JWT_REFRESH", "chippr_refresh_secret")
JWT_EXPIRATION_TIME = int(os.getenv("JWT_EXPIRATION_TIME", "3600"))  # 1 hour in seconds


# Cookie configuration
COOKIE_NAME = os.getenv("COOKIE_NAME", "access_token")
REFRESH_COOKIE_NAME = os.getenv("REFRESH_COOKIE_NAME", "refresh_token")
COOKIE_MAX_AGE = int(os.getenv("COOKIE_MAX_AGE", "3600"))  # 1 hour in seconds
REFRESH_TOKEN_EXPIRY = int(os.getenv("REFRESH_TOKEN_EXPIRY", "2592000"))
