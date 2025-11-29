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
COOKIE_NAME = os.getenv("COOKIE_NAME", "chippr_access_token")
REFRESH_COOKIE_NAME = os.getenv("REFRESH_COOKIE_NAME", "chippr_refresh_token")
COOKIE_MAX_AGE = int(os.getenv("COOKIE_MAX_AGE", "3600"))  # 1 hour in seconds
REFRESH_TOKEN_EXPIRY = int(os.getenv("REFRESH_TOKEN_EXPIRY", "2592000"))

# Supabase database configuration
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
MIGRATIONS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "database", "supabase", "migrations"
)

# Encryption configuration
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "is4ArmmmNSnGB13GZy9Kl2u8TWf0y441Ifxxdz7yVTw=")

# Plaid configuration
PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")
