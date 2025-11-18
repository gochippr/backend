"""
Example tests for database operations using the test database.
These tests demonstrate how to properly test database functionality.
"""
import pytest

from database.supabase import users


def test_database_connection(setup_test_db):
    """Test that we can connect to the test database."""
    # This test ensures the database is set up correctly
    assert setup_test_db is not None


def test_create_and_get_user(setup_test_db):
    """Test creating and retrieving a user."""
    # Test data
    user_data = {
        "sub": "test-user-123",
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/photo.jpg",
        "given_name": "Test",
        "family_name": "User",
        "email_verified": True,
        "provider": "google"
    }
    
    # Create user
    created_user = users.create_or_update_user(user_data)
    assert created_user is not None
    assert created_user["email"] == "test@example.com"
    assert created_user["name"] == "Test User"
    
    # Get user by ID
    retrieved_user = users.get_user_by_id("test-user-123")
    assert retrieved_user is not None
    assert retrieved_user["email"] == "test@example.com"
    
    # Get user by email
    retrieved_user_by_email = users.get_user_by_email("test@example.com")
    assert retrieved_user_by_email is not None
    assert retrieved_user_by_email["id"] == "test-user-123"


def test_update_existing_user(setup_test_db):
    """Test updating an existing user."""
    # Create initial user
    user_data = {
        "sub": "test-user-456",
        "email": "update@example.com",
        "name": "Original Name",
    }
    users.create_or_update_user(user_data)
    
    # Update user
    updated_data = {
        "sub": "test-user-456",
        "email": "update@example.com",
        "name": "Updated Name",
        "picture": "https://example.com/new-photo.jpg"
    }
    updated_user = users.create_or_update_user(updated_data)
    
    assert updated_user is not None
    assert updated_user["name"] == "Updated Name"
    assert updated_user["picture"] == "https://example.com/new-photo.jpg"


def test_delete_user(setup_test_db):
    """Test deleting a user."""
    # Create user
    user_data = {
        "sub": "test-user-789",
        "email": "delete@example.com",
        "name": "Delete Me",
    }
    users.create_or_update_user(user_data)
    
    # Verify user exists
    user = users.get_user_by_id("test-user-789")
    assert user is not None
    
    # Delete user
    deleted = users.delete_user("test-user-789")
    assert deleted is True
    
    # Verify user is gone
    user = users.get_user_by_id("test-user-789")
    assert user is None


def test_get_nonexistent_user(setup_test_db):
    """Test getting a user that doesn't exist."""
    user = users.get_user_by_id("nonexistent-user")
    assert user is None
    
    user_by_email = users.get_user_by_email("nonexistent@example.com")
    assert user_by_email is None 