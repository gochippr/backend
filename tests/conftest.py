import os
import tempfile
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from database.supabase import orm

# Set test environment variables FIRST
os.environ["TESTING"] = "true"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["PLAID_ENV"] = "sandbox"


@pytest.fixture(scope="function")
def setup_test_db():
    """Set up a fresh SQLite database for each test."""
    # Create a temporary file for the SQLite database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)  # Close the file descriptor, we just need the path
    
    # Set the database URL to use SQLite
    db_url = f"sqlite://{db_path}"
    os.environ["SUPABASE_DB_URL"] = db_url
    
    # Import and run migrations to set up the schema
    orm.run_migrations()
    
    yield db_url
    
    # Clean up the temporary database file
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="function")
def client(setup_test_db) -> Generator:
    """Create a test client with a fresh database for each test."""
    from main import app
    
    with TestClient(app) as c:
        yield c