import logging
from datetime import datetime
from typing import Optional, List
 

from pydantic import BaseModel
from database.supabase.orm import get_connection
from utils.database import row_to_model_with_cursor

logger = logging.getLogger(__name__)


class Account(BaseModel):
    id: str
    user_id: str
    plaid_item_id: str
    plaid_account_id: str
    name: Optional[str]
    official_name: Optional[str]
    mask: Optional[str]
    type: Optional[str]
    subtype: Optional[str]
    currency: Optional[str]
    current_balance: Optional[float]
    available_balance: Optional[float]
    created_at: datetime
    updated_at: Optional[datetime]


def get_account_by_id(account_id: str) -> Optional[Account]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM accounts WHERE id = %(id)s::uuid",
            {"id": account_id},
        )
        row = cur.fetchone()
        return row_to_model_with_cursor(row, Account, cur) if row else None
    finally:
        cur.close()
        conn.close()


def get_account_by_plaid_account_id(plaid_account_id: str) -> Optional[Account]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM accounts WHERE plaid_account_id = %(plaid_account_id)s",
            {"plaid_account_id": plaid_account_id},
        )
        row = cur.fetchone()
        return row_to_model_with_cursor(row, Account, cur) if row else None
    finally:
        cur.close()
        conn.close()


def list_accounts_for_user(user_id: str) -> List[Account]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM accounts WHERE user_id = %(user_id)s::uuid ORDER BY created_at DESC",
            {"user_id": user_id},
        )
        rows = cur.fetchall()
        return [row_to_model_with_cursor(r, Account, cur) for r in rows]
    finally:
        cur.close()
        conn.close()


def list_accounts_for_plaid_item(plaid_item_id: str) -> List[Account]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM accounts WHERE plaid_item_id = %(plaid_item_id)s::uuid ORDER BY created_at DESC",
            {"plaid_item_id": plaid_item_id},
        )
        rows = cur.fetchall()
        return [row_to_model_with_cursor(r, Account, cur) for r in rows]
    finally:
        cur.close()
        conn.close()


def upsert_account(
    user_id: str,
    plaid_item_id: str,
    plaid_account_id: str,
    name: Optional[str],
    official_name: Optional[str],
    mask: Optional[str],
    type: Optional[str],
    subtype: Optional[str],
    currency: Optional[str] = "USD",
    current_balance: Optional[float] = None,
    available_balance: Optional[float] = None,
) -> Account:
    conn = get_connection()
    cur = conn.cursor()
    try:
        sql = """
            INSERT INTO accounts (
                user_id, plaid_item_id, plaid_account_id, name, official_name, mask, type, subtype,
                currency, current_balance, available_balance
            )
            VALUES (
                %(user_id)s::uuid, %(plaid_item_id)s::uuid, %(plaid_account_id)s, %(name)s, %(official_name)s, %(mask)s,
                %(type)s, %(subtype)s, %(currency)s, %(current_balance)s, %(available_balance)s
            )
            ON CONFLICT (plaid_account_id) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                plaid_item_id = EXCLUDED.plaid_item_id,
                name = EXCLUDED.name,
                official_name = EXCLUDED.official_name,
                mask = EXCLUDED.mask,
                type = EXCLUDED.type,
                subtype = EXCLUDED.subtype,
                currency = EXCLUDED.currency,
                current_balance = EXCLUDED.current_balance,
                available_balance = EXCLUDED.available_balance,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
        """
        params = {
            "user_id": user_id,
            "plaid_item_id": plaid_item_id,
            "plaid_account_id": plaid_account_id,
            "name": name,
            "official_name": official_name,
            "mask": mask,
            "type": type,
            "subtype": subtype,
            "currency": currency,
            "current_balance": current_balance,
            "available_balance": available_balance,
        }
        cur.execute(sql, params)
        row = cur.fetchone()
        conn.commit()
        return row_to_model_with_cursor(row, Account, cur)
    except Exception as e:
        conn.rollback()
        logger.error(f"Error upserting account {plaid_account_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()
