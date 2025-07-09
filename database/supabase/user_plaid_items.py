from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel

from database.supabase.orm import get_connection
from utils.database import row_to_model_with_cursor


class UserPlaidItem(BaseModel):
    id: int
    user_id: str
    access_token: str
    item_id: str
    institution_id: Optional[str]
    institution_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    delete_at: Optional[datetime]
    is_active: bool


def insert_user_plaid_item(
    user_id: str,
    access_token: str,
    item_id: str,
    institution_id: Optional[str] = None,
    institution_name: Optional[str] = None,
) -> UserPlaidItem:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO user_plaid_items (
                user_id, access_token, item_id, institution_id, institution_name
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, item_id) DO NOTHING
            RETURNING *;
            """,
            (user_id, access_token, item_id, institution_id, institution_name),
        )
        result = cur.fetchone()
        if not result:
            raise Exception("Failed to insert user plaid item")

        conn.commit()
        return row_to_model_with_cursor(result, UserPlaidItem, cur)
    finally:
        cur.close()
        conn.close()


def update_user_plaid_item(item_id: str, user_id: str, **kwargs: Any) -> UserPlaidItem:
    conn = get_connection()
    cur = conn.cursor()
    try:
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = %s")
            values.append(value)
        values.extend([user_id, item_id])
        set_clause = ", ".join(fields)
        query = (
            f"UPDATE user_plaid_items SET {set_clause}, "
            f"updated_at = CURRENT_TIMESTAMP "
            f"WHERE user_id = %s AND item_id = %s "
            f"RETURNING *;"
        )
        cur.execute(query, values)
        result = cur.fetchone()
        if not result:
            raise Exception("Failed to update user plaid item")

        conn.commit()
        return row_to_model_with_cursor(result, UserPlaidItem, cur)
    finally:
        cur.close()
        conn.close()


def soft_delete_user_plaid_item(user_id: str, item_id: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE user_plaid_items
            SET is_active = FALSE, delete_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND item_id = %s
            """,
            (user_id, item_id),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_encrypted_token(user_id: str, item_id: str) -> Optional[str]:
    """Get encrypted access token for a specific user and item"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT access_token FROM user_plaid_items
            WHERE user_id = %s AND item_id = %s AND is_active = TRUE
            """,
            (user_id, item_id),
        )
        result = cur.fetchone()
        if result:
            return str(result[0])
        else:
            return None
    finally:
        cur.close()
        conn.close()


def get_user_items(user_id: str) -> List[UserPlaidItem]:
    """Get all active Plaid items for a user"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT *
            FROM user_plaid_items
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        items = []
        for row in cur.fetchall():
            items.append(row_to_model_with_cursor(row, UserPlaidItem, cur))
        return items
    finally:
        cur.close()
        conn.close()
