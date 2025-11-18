import logging
from datetime import datetime
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from utils.constants import SUPABASE_DB_URL

logger = logging.getLogger(__name__)


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Get a user by their ID (Google sub)"""
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            "SELECT * FROM users WHERE id = %s",
            (user_id,)
        )
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return dict(user) if user else None
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}")
        return None


def get_user_by_email(email: str) -> Optional[dict]:
    """Get a user by their email"""
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return dict(user) if user else None
    except Exception as e:
        logger.error(f"Error getting user by email: {e}")
        return None


def create_or_update_user(user_data: dict) -> Optional[dict]:
    """
    Create a new user or update existing user information.
    Uses upsert (INSERT ... ON CONFLICT ... UPDATE) to handle both cases.
    
    Args:
        user_data: Dictionary containing user information from OAuth provider
            Required fields: id (sub), email, name
            Optional fields: picture, given_name, family_name, email_verified, provider
    
    Returns:
        The created or updated user record, or None if operation failed
    """
    conn = None
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Prepare user data with defaults
        user_id = user_data.get("sub") or user_data.get("id")
        if not user_id:
            raise ValueError("User ID (sub) is required")
            
        email = user_data.get("email")
        if not email:
            raise ValueError("Email is required")
            
        name = user_data.get("name")
        if not name:
            raise ValueError("Name is required")
        
        # Upsert query - insert new user or update existing user
        cursor.execute("""
            INSERT INTO users (
                id, email, name, picture, given_name, family_name, 
                email_verified, provider, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                picture = EXCLUDED.picture,
                given_name = EXCLUDED.given_name,
                family_name = EXCLUDED.family_name,
                email_verified = EXCLUDED.email_verified,
                updated_at = EXCLUDED.updated_at
            RETURNING *
        """, (
            user_id,
            email,
            name,
            user_data.get("picture"),
            user_data.get("given_name"),
            user_data.get("family_name"),
            user_data.get("email_verified", False),
            user_data.get("provider", "google"),
            datetime.utcnow()
        ))
        
        user = cursor.fetchone()
        conn.commit()
        
        if user:
            logger.info(f"User created/updated successfully: {email}")
        
        cursor.close()
        conn.close()
        
        return dict(user) if user else None
        
    except Exception as e:
        logger.error(f"Error creating/updating user: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return None


def delete_user(user_id: str) -> bool:
    """
    Delete a user by their ID.
    Note: This is a hard delete. Consider implementing soft delete if needed.
    
    Args:
        user_id: The user's ID (Google sub)
    
    Returns:
        True if user was deleted, False otherwise
    """
    conn = None
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM users WHERE id = %s",
            (user_id,)
        )
        
        deleted = cursor.rowcount > 0
        conn.commit()
        
        cursor.close()
        conn.close()
        
        if deleted:
            logger.info(f"User deleted successfully: {user_id}")
        
        return deleted
        
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False