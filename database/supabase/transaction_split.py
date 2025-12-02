import logging
from datetime import datetime, date
from typing import Optional, List
 

from pydantic import BaseModel
from database.supabase.orm import get_connection
from utils.database import row_to_model_with_cursor

logger = logging.getLogger(__name__)


class Transaction(BaseModel):
    id: str
    account_id: str
    external_txn_id: Optional[str]
    amount: float
    currency: Optional[str]
    type: str  # 'debit' | 'credit' (enforced in code)
    merchant_name: Optional[str]
    description: Optional[str]
    category: Optional[str]
    authorized_date: Optional[date]
    posted_date: Optional[date]
    pending: bool
    original_payer_user_id: Optional[str]
    created_at: datetime


def get_transaction_by_id(txn_id: str) -> Optional[Transaction]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM transactions WHERE id = %(id)s", {"id": txn_id})
        row = cur.fetchone()
        return row_to_model_with_cursor(row, Transaction, cur) if row else None
    finally:
        cur.close()
        conn.close()


def get_transaction_by_external_id(external_txn_id: str) -> Optional[Transaction]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM transactions WHERE external_txn_id = %(external_txn_id)s",
            {"external_txn_id": external_txn_id},
        )
        row = cur.fetchone()
        return row_to_model_with_cursor(row, Transaction, cur) if row else None
    finally:
        cur.close()
        conn.close()


def list_transactions_for_account(
    account_id: str,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> List[Transaction]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        if date_from and date_to:
            cur.execute(
                """
                SELECT * FROM transactions
                WHERE account_id = %(account_id)s
                  AND posted_date >= %(date_from)s
                  AND posted_date <= %(date_to)s
                ORDER BY posted_date DESC, created_at DESC
                """,
                {"account_id": account_id, "date_from": date_from, "date_to": date_to},
            )
        else:
            cur.execute(
                """
                SELECT * FROM transactions
                WHERE account_id = %(account_id)s
                ORDER BY posted_date DESC NULLS LAST, created_at DESC
                """,
                {"account_id": account_id},
            )
        rows = cur.fetchall()
        return [row_to_model_with_cursor(r, Transaction, cur) for r in rows]
    finally:
        cur.close()
        conn.close()


def upsert_transaction(
    account_id: str,
    external_txn_id: Optional[str],
    amount: float,
    currency: Optional[str],
    type: str,
    merchant_name: Optional[str],
    description: Optional[str],
    category: Optional[str],
    authorized_date: Optional[date],
    posted_date: Optional[date],
    pending: bool,
    original_payer_user_id: Optional[str],
) -> Transaction:
    conn = get_connection()
    cur = conn.cursor()
    try:
        if external_txn_id:
            sql = """
                INSERT INTO transactions (
                    account_id, external_txn_id, amount, currency, type, merchant_name, description, category,
                    authorized_date, posted_date, pending, original_payer_user_id
                )
                VALUES (
                    %(account_id)s, %(external_txn_id)s, %(amount)s, %(currency)s, %(type)s, %(merchant_name)s,
                    %(description)s, %(category)s, %(authorized_date)s, %(posted_date)s, %(pending)s,
                    %(original_payer_user_id)s
                )
                ON CONFLICT (external_txn_id) DO UPDATE SET
                    account_id = EXCLUDED.account_id,
                    amount = EXCLUDED.amount,
                    currency = EXCLUDED.currency,
                    type = EXCLUDED.type,
                    merchant_name = EXCLUDED.merchant_name,
                    description = EXCLUDED.description,
                    category = EXCLUDED.category,
                    authorized_date = EXCLUDED.authorized_date,
                    posted_date = EXCLUDED.posted_date,
                    pending = EXCLUDED.pending,
                    original_payer_user_id = EXCLUDED.original_payer_user_id
                RETURNING *
            """
        else:
            sql = """
                INSERT INTO transactions (
                    account_id, amount, currency, type, merchant_name, description, category,
                    authorized_date, posted_date, pending, original_payer_user_id
                )
                VALUES (
                    %(account_id)s, %(amount)s, %(currency)s, %(type)s, %(merchant_name)s, %(description)s,
                    %(category)s, %(authorized_date)s, %(posted_date)s, %(pending)s, %(original_payer_user_id)s
                )
                RETURNING *
            """

        params = {
            "account_id": account_id,
            "external_txn_id": external_txn_id,
            "amount": amount,
            "currency": currency,
            "type": type,
            "merchant_name": merchant_name,
            "description": description,
            "category": category,
            "authorized_date": authorized_date,
            "posted_date": posted_date,
            "pending": pending,
            "original_payer_user_id": original_payer_user_id,
        }

        cur.execute(sql, params)
        row = cur.fetchone()
        conn.commit()
        return row_to_model_with_cursor(row, Transaction, cur)
    except Exception as e:
        conn.rollback()
        logger.error(f"Error upserting transaction (external={external_txn_id}): {e}")
        raise
    finally:
        cur.close()
        conn.close()
