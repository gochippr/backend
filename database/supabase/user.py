import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from database.supabase.orm import get_connection
from utils.database import row_to_model_with_cursor

logger = logging.getLogger(__name__)


class User(BaseModel):
    id: UUID
    idp_id: str
    email: str
    username: Optional[str]
    given_name: Optional[str]
    family_name: Optional[str]
    full_name: Optional[str]
    photo_url: Optional[str]
    email_verified: bool
    provider: str
    locale: Optional[str]
    timezone: Optional[str]
    is_active: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


def get_user_by_idp_id_and_provider(idp_id: str, provider: str) -> Optional[User]:
    """
    Get user by IDP ID and provider.

    Args:
        idp_id: Identity provider ID
        provider: Provider name (google, apple, etc.)

    Returns:
        User model or None if not found
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT * FROM users WHERE idp_id = %s AND provider = %s
        """,
            (idp_id, provider),
        )

        result = cur.fetchone()
        return row_to_model_with_cursor(result, User, cur) if result else None

    except Exception as e:
        logger.error(f"Error getting user by IDP ID {idp_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def get_user_by_email(email: str) -> Optional[User]:
    """
    Get user by email.

    Args:
        email: User email

    Returns:
        User model or None if not found
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT * FROM users WHERE email = %s
        """,
            (email,),
        )

        result = cur.fetchone()
        return row_to_model_with_cursor(result, User, cur) if result else None

    except Exception as e:
        logger.error(f"Error getting user by email {email}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def get_user_by_id(user_id: UUID) -> Optional[User]:
    """
    Get user by UUID.

    Args:
        user_id: User UUID

    Returns:
        User model or None if not found
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT * FROM users WHERE id = %s
        """,
            (user_id,),
        )

        result = cur.fetchone()
        return row_to_model_with_cursor(result, User, cur) if result else None

    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def create_user(
    idp_id: str,
    email: str,
    given_name: Optional[str],
    family_name: Optional[str],
    full_name: Optional[str],
    photo_url: Optional[str],
    email_verified: bool,
    provider: str,
) -> User:
    """
    Create a new user in the database.

    Args:
        idp_id: Identity provider ID
        email: User email
        given_name: First name
        family_name: Last name
        full_name: Full name
        photo_url: Profile photo URL
        email_verified: Whether email is verified
        provider: Identity provider (google, apple, etc.)

    Returns:
        User model of the created user
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO users (
                idp_id, email, given_name, family_name, full_name,
                photo_url, email_verified, provider
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """,
            (
                idp_id,
                email,
                given_name,
                family_name,
                full_name,
                photo_url,
                email_verified,
                provider,
            ),
        )

        result = cur.fetchone()
        conn.commit()
        return row_to_model_with_cursor(result, User, cur)

    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating user {email}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def update_user_info(
    user_id: UUID,
    idp_id: Optional[str] = None,
    given_name: Optional[str] = None,
    family_name: Optional[str] = None,
    full_name: Optional[str] = None,
    photo_url: Optional[str] = None,
    email_verified: Optional[bool] = None,
    provider: Optional[str] = None,
) -> User:
    """
    Update user information.

    Args:
        user_id: User UUID
        idp_id: Identity provider ID
        given_name: First name
        family_name: Last name
        full_name: Full name
        photo_url: Profile photo URL
        email_verified: Whether email is verified
        provider: Identity provider

    Returns:
        Updated User model
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Build dynamic update query
        update_fields = []
        params = []

        if idp_id is not None:
            update_fields.append("idp_id = %s")
            params.append(idp_id)
        if given_name is not None:
            update_fields.append("given_name = %s")
            params.append(given_name)
        if family_name is not None:
            update_fields.append("family_name = %s")
            params.append(family_name)
        if full_name is not None:
            update_fields.append("full_name = %s")
            params.append(full_name)
        if photo_url is not None:
            update_fields.append("photo_url = %s")
            params.append(photo_url)
        if email_verified is not None:
            update_fields.append("email_verified = %s")
            params.append(str(email_verified))
        if provider is not None:
            update_fields.append("provider = %s")
            params.append(provider)

        if not update_fields:
            # If nothing to update, just return the current user
            current_user = get_user_by_id(user_id)
            if current_user is None:
                raise Exception(f"User {user_id} not found")
            return current_user

        update_fields.append("last_login_at = CURRENT_TIMESTAMP")
        update_fields.append("updated_at = CURRENT_TIMESTAMP")

        query = f"""
            UPDATE users SET {", ".join(update_fields)}
            WHERE id = %s
            RETURNING *
        """
        params.append(str(user_id))

        cur.execute(query, params)
        result = cur.fetchone()
        if not result:
            raise Exception(f"Failed to update user {user_id}")

        conn.commit()
        return row_to_model_with_cursor(result, User, cur)

    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating user {user_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def update_user_last_login(user_id: UUID) -> None:
    """
    Update user's last login timestamp.

    Args:
        user_id: User UUID
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            UPDATE users SET last_login_at = CURRENT_TIMESTAMP 
            WHERE id = %s
        """,
            (user_id,),
        )

        conn.commit()

    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating last login for user {user_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()
