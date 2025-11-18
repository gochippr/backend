import os

# Set test environment variables FIRST
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["PLAID_ENV"] = "sandbox"
os.environ["SUPABASE_DB_URL"] = "postgresql://testuser:testpass@localhost:5432/testdb"

# Now do the imports
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def client() -> Generator:
    with TestClient(app) as c:
        yield c