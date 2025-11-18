import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient

# Set test environment variables FIRST
os.environ["TESTING"] = "true"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["PLAID_ENV"] = "sandbox"

# Use PostgreSQL test database URL
TEST_DATABASE_URL = os.getenv("SUPABASE_DB_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
os.environ["SUPABASE_DB_URL"] = TEST_DATABASE_URL


@pytest.fixture(scope="function")
def setup_test_db():
    """Set up test database connection."""
    # For Docker-based testing, the database is already set up
    # Just yield the database URL for tests that need it
    yield TEST_DATABASE_URL


@pytest.fixture(scope="function")
def client(setup_test_db) -> Generator:
    """Create a test client with a fresh database for each test."""
    from main import app
    
    with TestClient(app) as c:
        yield c