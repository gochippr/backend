import logging
from datetime import datetime
from typing import Optional
 

from pydantic import BaseModel

from database.supabase.orm import get_connection
from utils.database import row_to_model_with_cursor

logger = logging.getLogger(__name__)


class User(BaseModel):
    id: str
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
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM users WHERE idp_id = %(idp_id)s AND provider = %(provider)s",
            {"idp_id": idp_id, "provider": provider},
        )
        row = cur.fetchone()
        return row_to_model_with_cursor(row, User, cur) if row else None
    except Exception as e:
        logger.error(f"Error getting user by IDP ID {idp_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def get_user_by_email(email: str) -> Optional[User]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM users WHERE email = %(email)s",
            {"email": email},
        )
        row = cur.fetchone()
        return row_to_model_with_cursor(row, User, cur) if row else None
    except Exception as e:
        logger.error(f"Error getting user by email {email}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def get_user_by_id(user_id: str) -> Optional[User]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM users WHERE id = %(id)s::uuid",
            {"id": user_id},
        )
        row = cur.fetchone()
        return row_to_model_with_cursor(row, User, cur) if row else None
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
    conn = get_connection()
    cur = conn.cursor()
    try:
        sql = """
            INSERT INTO users (
                idp_id, email, given_name, family_name, full_name,
                photo_url, email_verified, provider
            ) VALUES (
                %(idp_id)s, %(email)s, %(given_name)s, %(family_name)s, %(full_name)s,
                %(photo_url)s, %(email_verified)s, %(provider)s
            )
            RETURNING *
        """
        params = {
            "idp_id": idp_id,
            "email": email,
            "given_name": given_name,
            "family_name": family_name,
            "full_name": full_name,
            "photo_url": photo_url,
            "email_verified": email_verified,
            "provider": provider,
        }
        cur.execute(sql, params)
        row = cur.fetchone()
        conn.commit()
        return row_to_model_with_cursor(row, User, cur)
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating user {email}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def update_user_info(
    user_id: str,
    idp_id: Optional[str] = None,
    given_name: Optional[str] = None,
    family_name: Optional[str] = None,
    full_name: Optional[str] = None,
    photo_url: Optional[str] = None,
    email_verified: Optional[bool] = None,
    provider: Optional[str] = None,
) -> User:
    conn = get_connection()
    cur = conn.cursor()
    try:
        fields: dict = {}
        if idp_id is not None:
            fields["idp_id"] = idp_id
        if given_name is not None:
            fields["given_name"] = given_name
        if family_name is not None:
            fields["family_name"] = family_name
        if full_name is not None:
            fields["full_name"] = full_name
        if photo_url is not None:
            fields["photo_url"] = photo_url
        if email_verified is not None:
            fields["email_verified"] = email_verified
        if provider is not None:
            fields["provider"] = provider

        if not fields:
            current = get_user_by_id(user_id)
            if current is None:
                raise Exception(f"User {user_id} not found")
            return current

        set_clause = ", ".join([f"{k} = %({k})s" for k in fields.keys()])
        set_clause += ", last_login_at = CURRENT_TIMESTAMP"
        set_clause += ", updated_at = CURRENT_TIMESTAMP"

        sql = f"""
            UPDATE users
            SET {set_clause}
            WHERE id = %(user_id)s::uuid
            RETURNING *
        """
        params = {**fields, "user_id": user_id}
        cur.execute(sql, params)
        row = cur.fetchone()
        if not row:
            raise Exception(f"Failed to update user {user_id}")
        conn.commit()
        return row_to_model_with_cursor(row, User, cur)
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating user {user_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def update_user_last_login(user_id: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = %(id)s::uuid",
            {"id": user_id},
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating last login for user {user_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()
