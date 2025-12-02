import logging
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel
from database.supabase.orm import get_connection
from utils.database import row_to_model_with_cursor

logger = logging.getLogger(__name__)


class PlaidItem(BaseModel):
    id: str
    user_id: str
    access_token: str
    item_id: str
    institution_id: Optional[str]
    institution_name: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]


def get_plaid_item_by_id(item_pk: str) -> Optional[PlaidItem]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM plaid_items WHERE id = %(id)s::uuid",
            {"id": item_pk},
        )
        row = cur.fetchone()
        return row_to_model_with_cursor(row, PlaidItem, cur) if row else None
    finally:
        cur.close()
        conn.close()


def get_plaid_item_by_user_and_item(user_id: str, item_id: str) -> Optional[PlaidItem]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM plaid_items WHERE user_id = %(user_id)s::uuid AND item_id = %(item_id)s",
            {"user_id": user_id, "item_id": item_id},
        )
        row = cur.fetchone()
        return row_to_model_with_cursor(row, PlaidItem, cur) if row else None
    finally:
        cur.close()
        conn.close()


def list_plaid_items_for_user(user_id: str) -> List[PlaidItem]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM plaid_items WHERE user_id = %(user_id)s::uuid ORDER BY created_at DESC",
            {"user_id": user_id},
        )
        rows = cur.fetchall()
        return [row_to_model_with_cursor(r, PlaidItem, cur) for r in rows]
    finally:
        cur.close()
        conn.close()


def create_or_update_plaid_item(
    user_id: str,
    access_token: str,
    item_id: str,
    institution_id: Optional[str],
    institution_name: Optional[str],
    is_active: bool = True,
) -> PlaidItem:
    conn = get_connection()
    cur = conn.cursor()
    try:
        sql = """
            INSERT INTO plaid_items (user_id, access_token, item_id, institution_id, institution_name, is_active)
            VALUES (%(user_id)s::uuid, %(access_token)s, %(item_id)s, %(institution_id)s, %(institution_name)s, %(is_active)s)
            ON CONFLICT (user_id, item_id) DO UPDATE SET
                access_token = EXCLUDED.access_token,
                institution_id = EXCLUDED.institution_id,
                institution_name = EXCLUDED.institution_name,
                is_active = EXCLUDED.is_active,
                updated_at = CURRENT_TIMESTAMP,
                deleted_at = NULL
            RETURNING *
        """
        params = {
            "user_id": user_id,
            "access_token": access_token,
            "item_id": item_id,
            "institution_id": institution_id,
            "institution_name": institution_name,
            "is_active": is_active,
        }
        cur.execute(sql, params)
        row = cur.fetchone()
        conn.commit()
        return row_to_model_with_cursor(row, PlaidItem, cur)
    except Exception as e:
        conn.rollback()
        logger.error(f"Error upserting plaid_item (user_id={user_id}, item_id={item_id}): {e}")
        raise
    finally:
        cur.close()
        conn.close()


def deactivate_plaid_item(item_pk: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE plaid_items
            SET is_active = FALSE, deleted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = %(id)s::uuid
            """,
            {"id": item_pk},
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error deactivating plaid_item {item_pk}: {e}")
        raise
    finally:
        cur.close()
        conn.close()
