import logging
from datetime import date, datetime
from typing import Any, Iterable, List, Optional, Tuple

from psycopg2.extensions import connection as PGConnection
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


def list_transactions_for_user(user_id: str) -> List[Transaction]:
    """Return all transactions for the given user ordered from newest to oldest."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT t.*
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = %(user_id)s::uuid
              AND (t.deleted_at IS NULL)
            ORDER BY COALESCE(t.posted_date, t.authorized_date) DESC NULLS LAST,
                     t.created_at DESC
            """,
            {"user_id": user_id},
        )
        rows = cur.fetchall()
        return [row_to_model_with_cursor(r, Transaction, cur) for r in rows]
    finally:
        cur.close()
        conn.close()


def get_spending_by_category_for_user(
    user_id: str,
    *,
    start_date: date,
    end_date_exclusive: date,
) -> List[Tuple[str, float]]:
    """Aggregate debit transactions by category for a user within a date range."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                COALESCE(NULLIF(t.category, ''), 'uncategorized') AS category,
                SUM(t.amount) AS total_amount
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = %(user_id)s::uuid
              AND t.type = 'debit'
              AND t.pending = FALSE
              AND t.deleted_at IS NULL
              AND t.posted_date >= %(start_date)s
              AND t.posted_date < %(end_date)s
            GROUP BY category
            ORDER BY total_amount DESC
            """,
            {
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date_exclusive,
            },
        )
        rows = cur.fetchall()
        results: List[Tuple[str, float]] = []
        for category, total in rows:
            total_float = float(total) if total is not None else 0.0
            results.append((category, total_float))
        return results
    finally:
        cur.close()
        conn.close()


def get_transaction_by_id(txn_id: str) -> Optional[Transaction]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM transactions WHERE id = %(id)s::uuid",
            {"id": txn_id},
        )
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
                WHERE account_id = %(account_id)s::uuid
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
                WHERE account_id = %(account_id)s::uuid
                ORDER BY posted_date DESC NULLS LAST, created_at DESC
                """,
                {"account_id": account_id},
            )
        rows = cur.fetchall()
        return [row_to_model_with_cursor(r, Transaction, cur) for r in rows]
    finally:
        cur.close()
        conn.close()


def list_uncategorized_transactions_for_user(
    conn: PGConnection,
    *,
    user_id: str,
    limit: Optional[int] = None,
) -> List[Transaction]:
    cur = conn.cursor()
    try:
        query = (
            """
            SELECT t.*
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = %(user_id)s::uuid
              AND (t.category IS NULL OR t.category = '')
              AND t.deleted_at IS NULL
            ORDER BY t.posted_date DESC NULLS LAST, t.created_at DESC
            """
        )
        params: dict[str, Any] = {"user_id": user_id}
        if limit is not None:
            query += " LIMIT %(limit)s"
            params["limit"] = limit

        cur.execute(query, params)
        rows = cur.fetchall()
        return [row_to_model_with_cursor(r, Transaction, cur) for r in rows]
    finally:
        cur.close()


def update_transaction_category(
    conn: PGConnection,
    *,
    transaction_id: str,
    category: str,
) -> int:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE transactions
            SET category = %(category)s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %(transaction_id)s::uuid
              AND deleted_at IS NULL
            """,
            {"transaction_id": transaction_id, "category": category},
        )
        return cur.rowcount
    finally:
        cur.close()


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
                    %(account_id)s::uuid, %(external_txn_id)s, %(amount)s, %(currency)s, %(type)s, %(merchant_name)s,
                    %(description)s, %(category)s, %(authorized_date)s, %(posted_date)s, %(pending)s,
                    %(original_payer_user_id)s::uuid
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
                    %(account_id)s::uuid, %(amount)s, %(currency)s, %(type)s, %(merchant_name)s, %(description)s,
                    %(category)s, %(authorized_date)s, %(posted_date)s, %(pending)s, %(original_payer_user_id)s::uuid
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


def upsert_transaction_added(conn: PGConnection, *, data: dict[str, Any]) -> None:
    """Upsert (or undelete) a Plaid-added transaction using an existing connection."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO transactions (
            account_id, external_txn_id, amount, currency, type, merchant_name, description, category,
            authorized_date, posted_date, pending, original_payer_user_id
        )
        VALUES (
            %(account_id)s::uuid, %(external_txn_id)s, %(amount)s, %(currency)s, %(type)s, %(merchant_name)s,
            %(description)s, %(category)s, %(authorized_date)s, %(posted_date)s, %(pending)s,
            %(original_payer_user_id)s::uuid
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
            original_payer_user_id = EXCLUDED.original_payer_user_id,
            updated_at = CURRENT_TIMESTAMP,
            deleted_at = NULL
        """,
        data,
    )


def apply_transaction_modified(conn: PGConnection, *, data: dict[str, Any]) -> None:
    """Update mutable fields on an existing transaction."""
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE transactions
        SET amount = %(amount)s,
            currency = %(currency)s,
            type = %(type)s,
            merchant_name = %(merchant_name)s,
            description = %(description)s,
            category = %(category)s,
            authorized_date = %(authorized_date)s,
            posted_date = %(posted_date)s,
            pending = %(pending)s,
            updated_at = CURRENT_TIMESTAMP
        WHERE external_txn_id = %(external_txn_id)s
        """,
        data,
    )


def apply_transaction_removed(
    conn: PGConnection,
    *,
    user_id: str,
    external_txn_ids: Iterable[str],
) -> int:
    """Soft delete transactions by external id for the given user."""
    ids = list(external_txn_ids)
    if not ids:
        return 0

    cur = conn.cursor()
    cur.execute(
        """
        UPDATE transactions t
        SET deleted_at = COALESCE(t.deleted_at, CURRENT_TIMESTAMP), updated_at = CURRENT_TIMESTAMP
        FROM accounts a
        WHERE t.account_id = a.id
          AND a.user_id = %(user_id)s::uuid
          AND t.external_txn_id = ANY(%(ids)s)
        """,
        {"user_id": user_id, "ids": ids},
    )
    return cur.rowcount


def relink_pending_to_posted(
    conn: PGConnection,
    *,
    pending_transaction_id: str,
    posted_transaction_id: str,
    posted_data: dict[str, Any],
) -> bool:
    """Relink a pending transaction row to its posted counterpart if it exists."""
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE transactions
        SET external_txn_id = %(posted_id)s,
            amount = %(amount)s,
            currency = %(currency)s,
            type = %(type)s,
            merchant_name = %(merchant_name)s,
            description = %(description)s,
            category = %(category)s,
            authorized_date = %(authorized_date)s,
            posted_date = %(posted_date)s,
            pending = FALSE,
            updated_at = CURRENT_TIMESTAMP
        WHERE external_txn_id = %(pending_id)s
        """,
        {
            "posted_id": posted_transaction_id,
            "pending_id": pending_transaction_id,
            **posted_data,
        },
    )
    return cur.rowcount > 0
