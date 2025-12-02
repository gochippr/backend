import logging
from datetime import datetime
from typing import Optional, List
 

from pydantic import BaseModel
from database.supabase.orm import get_connection
from utils.database import row_to_model_with_cursor

logger = logging.getLogger(__name__)


class Settlement(BaseModel):
    id: str
    from_user_id: str
    to_user_id: str
    amount: float
    currency: Optional[str]
    method: Optional[str]  # enforced in code
    related_txn_id: Optional[str]
    created_at: datetime


def get_settlement_by_id(sid: str) -> Optional[Settlement]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM settlements WHERE id = %(id)s::uuid",
            {"id": sid},
        )
        row = cur.fetchone()
        return row_to_model_with_cursor(row, Settlement, cur) if row else None
    finally:
        cur.close()
        conn.close()


def list_settlements_between_users(a: str, b: str) -> List[Settlement]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT * FROM settlements
            WHERE (from_user_id = %(a)s::uuid AND to_user_id = %(b)s::uuid)
               OR (from_user_id = %(b)s::uuid AND to_user_id = %(a)s::uuid)
            ORDER BY created_at DESC
            """,
            {"a": a, "b": b},
        )
        rows = cur.fetchall()
        return [row_to_model_with_cursor(r, Settlement, cur) for r in rows]
    finally:
        cur.close()
        conn.close()


def create_settlement(
    from_user_id: str,
    to_user_id: str,
    amount: float,
    currency: Optional[str],
    method: Optional[str],
    related_txn_id: Optional[str] = None,
) -> Settlement:
    conn = get_connection()
    cur = conn.cursor()
    try:
        sql = """
            INSERT INTO settlements (from_user_id, to_user_id, amount, currency, method, related_txn_id)
            VALUES (%(from_user_id)s, %(to_user_id)s, %(amount)s, %(currency)s, %(method)s, %(related_txn_id)s)
            RETURNING *
        """
        params = {
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "amount": amount,
            "currency": currency,
            "method": method,
            "related_txn_id": related_txn_id,
        }
        cur.execute(sql, params)
        row = cur.fetchone()
        conn.commit()
        return row_to_model_with_cursor(row, Settlement, cur)
    except Exception as e:
        conn.rollback()
        logger.error(
            f"Error creating settlement {from_user_id}->{to_user_id} amount={amount}: {e}"
        )
        raise
    finally:
        cur.close()
        conn.close()
