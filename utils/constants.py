import os

from dotenv import load_dotenv

load_dotenv(".env.local")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

API_URL = os.getenv("API_URL", "http://localhost:8000")
APP_SCHEME = os.getenv("APP_SCHEME", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
JWT_SECRET = os.getenv("JWT_SECRET", "chippr_secret")
JWT_REFRESH_SECRET = os.getenv("JWT_REFRESH", "chippr_refresh_secret")
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8081")
