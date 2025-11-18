import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient

# Set test environment variables
os.environ["DATABASE_URL"] = "postgresql://testuser:testpass@localhost:5432/testdb"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["PLAID_ENV"] = "sandbox"

from app.main import app


@pytest.fixture(scope="module")
def client() -> Generator:
    with TestClient(app) as c:
        yield c