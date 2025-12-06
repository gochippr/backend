# Chippr Backend

A FastAPI-based backend for Chippr, a gamified personal finance application that helps users track spending, split bills with friends, and stay within budget through streak-based challenges.

---

## Technology Stack

| Category | Technology | Version |
|----------|------------|---------|
| **Language** | Python | >= 3.10 |
| **Framework** | FastAPI | >= 0.115 |
| **Database** | PostgreSQL (via Supabase) | 15+ |
| **ORM/DB Driver** | psycopg2-binary | >= 2.9 |
| **Validation** | Pydantic | >= 2.11 |
| **Auth** | Google OAuth 2.0, JWT (PyJWT) | - |
| **Banking Integration** | Plaid API | >= 34.0 |
| **AI/LLM** | Google Generative AI (Gemini) | >= 1.38 |
| **Package Manager** | uv | latest |
| **Server** | Uvicorn (ASGI) | >= 0.35 |

### Dev Dependencies
- **Linting**: Ruff
- **Type Checking**: Pyrefly

---

## Style Guide

This project follows:

- **[PEP 8](https://peps.python.org/pep-0008/)** - Python code style
- **[FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)** - API design patterns
- **snake_case** for all variable names, function names, and API response fields
- **Pydantic models** in `models/` directory, separate from routers
- **Database access** in `database/supabase/` with dedicated files per entity
- **Business logic** in `business/` directory with service modules

---

## Operation Instructions

### Prerequisites

1. **Python 3.10+** installed
2. **uv** package manager installed:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. **PostgreSQL** database (or Supabase project)

### Environment Setup

Create a `.env.local` file in the project root:

```bash
# Database
SUPABASE_DB_URL=postgresql://user:password@host:5432/database

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Plaid (Banking)
PLAID_CLIENT_ID=your-plaid-client-id
PLAID_SECRET=your-plaid-secret
PLAID_ENV=sandbox  # or 'development', 'production'

# Google AI (Gemini)
GOOGLE_API_KEY=your-gemini-api-key

# JWT (change in production!)
JWT_SECRET=your-secure-jwt-secret
JWT_REFRESH=your-secure-refresh-secret

# Optional
API_URL=http://localhost:8000
WEBAPP_URL=http://localhost:8081
IS_DEV=true
```

### Install Dependencies

```bash
uv sync
```

### Run the Application

```bash
./entrypoint.sh
```

Or manually:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Run with Docker

```bash
docker-compose up
```

---

## Limitations

### Incomplete Functionality

| Feature | Status | Notes |
|---------|--------|-------|
| **Leaderboard** | Placeholder | Returns only current user's stats; no friend comparison yet |
| **Push Notifications** | Not implemented | Daily budget challenge notifications described in UX but not built |
| **Perfect Week Badge** | Partial | Badge defined but automatic detection not implemented |
| **Transaction Categorization** | AI-dependent | Requires valid `GOOGLE_API_KEY` for Gemini; falls back gracefully |

### Hard-coded Values

| Item | Location | Value |
|------|----------|-------|
| **CORS Origins** | `main.py` | `localhost:8081`, `localhost:3000`, `localhost:5173` |
| **Default JWT Secret** | `utils/constants.py` | `"chippr_secret"` (override in production!) |
| **Default Encryption Key** | `utils/constants.py` | Hard-coded base64 key (override in production!) |
| **Default Daily Budget** | `business/budget_run/service.py` | `$50.00` base, +20% weekends, +10% Fridays |
| **JWT Expiration** | `utils/constants.py` | 1 hour (3600 seconds) |
| **Refresh Token Expiry** | `utils/constants.py` | 30 days (2592000 seconds) |
| **Plaid Environment** | `utils/constants.py` | `"sandbox"` (change for production) |

### Known Issues

- Database migrations run on every startup (idempotent but not tracked)
- No rate limiting implemented
- No request validation middleware for payload size
- User deletion cascades are handled at DB level only

---

## API Endpoints

| Prefix | Description |
|--------|-------------|
| `/auth/*` | Google OAuth, token refresh, logout |
| `/users/*` | User profile management |
| `/accounts` | Linked bank accounts |
| `/transactions` | Transaction history and summaries |
| `/plaid/*` | Plaid Link integration |
| `/friends/*` | Friend requests and relationships |
| `/splits/*` | Bill splitting with friends |
| `/budget-run/*` | Daily Budget Run game (streaks, badges, challenges) |
| `/ai/*` | AI-powered features |

---

## License

Proprietary - Chippr Team
