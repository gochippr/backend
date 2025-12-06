import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence

from pydantic import BaseModel

from database.supabase.orm import get_connection
from utils.database import row_to_model_with_cursor

logger = logging.getLogger(__name__)


class TransactionSplit(BaseModel):
    id: str
    transaction_id: str
    debtor_user_id: str
    amount: float
    share_weight: Optional[float]
    note: Optional[str]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]


class FriendSplitBalance(BaseModel):
    friend_user_id: str
    amount_owed_to_user: float
    amount_user_owes: float


class SplitWithTransaction(BaseModel):
    id: str
    transaction_id: str
    debtor_user_id: str
    amount: float
    share_weight: Optional[float]
    note: Optional[str]
    created_at: datetime
    updated_at: datetime
    payer_user_id: str
    transaction_amount: float
    transaction_currency: Optional[str]
    transaction_type: str
    transaction_description: Optional[str]
    merchant_name: Optional[str]
    category: Optional[str]
    authorized_date: Optional[date]
    posted_date: Optional[date]


def _decimal_to_float(value: Decimal | None) -> float:
    return float(value) if value is not None else 0.0


def list_splits_for_transaction(transaction_id: str) -> List[TransactionSplit]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT * FROM transaction_splits
            WHERE transaction_id = %(transaction_id)s::uuid
              AND deleted_at IS NULL
            ORDER BY created_at ASC
            """,
            {"transaction_id": transaction_id},
        )
        rows = cur.fetchall()
        return [row_to_model_with_cursor(r, TransactionSplit, cur) for r in rows]
    finally:
        cur.close()
        conn.close()


def list_splits_for_transactions(transaction_ids: Iterable[str]) -> Dict[str, List[TransactionSplit]]:
    ids = list(transaction_ids)
    if not ids:
        return {}

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT *
            FROM transaction_splits
            WHERE transaction_id = ANY(%(ids)s::uuid[])
              AND deleted_at IS NULL
            ORDER BY created_at ASC
            """,
            {"ids": ids},
        )
        rows = cur.fetchall()
        grouped: Dict[str, List[TransactionSplit]] = {tid: [] for tid in ids}
        for row in rows:
            split = row_to_model_with_cursor(row, TransactionSplit, cur)
            grouped.setdefault(split.transaction_id, []).append(split)
        return grouped
    finally:
        cur.close()
        conn.close()


def sum_splits_for_transactions(transaction_ids: Iterable[str]) -> Dict[str, float]:
    ids = list(transaction_ids)
    if not ids:
        return {}

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT transaction_id, SUM(amount) AS total_amount
            FROM transaction_splits
            WHERE transaction_id = ANY(%(ids)s::uuid[])
              AND deleted_at IS NULL
            GROUP BY transaction_id
            """,
            {"ids": ids},
        )
        rows = cur.fetchall()
        return {
            row[0]: _decimal_to_float(row[1])
            for row in rows
            if row and row[0]
        }
    finally:
        cur.close()
        conn.close()


def replace_transaction_splits(
    *,
    transaction_id: str,
    splits: Sequence[Dict[str, Any]],
) -> List[TransactionSplit]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, debtor_user_id
            FROM transaction_splits
            WHERE transaction_id = %(transaction_id)s::uuid
              AND deleted_at IS NULL
            """,
            {"transaction_id": transaction_id},
        )
        existing_rows = cur.fetchall()
        existing_by_debtor = {row[1]: row[0] for row in existing_rows}

        retained_ids: List[str] = []
        result_rows: List[Any] = []

        for split in splits:
            debtor_user_id = split["debtor_user_id"]
            amount = split["amount"]
            share_weight = split.get("share_weight")
            note = split.get("note")

            if debtor_user_id in existing_by_debtor:
                split_id = existing_by_debtor[debtor_user_id]
                cur.execute(
                    """
                    UPDATE transaction_splits
                    SET amount = %(amount)s,
                        share_weight = %(share_weight)s,
                        note = %(note)s,
                        updated_at = CURRENT_TIMESTAMP,
                        deleted_at = NULL
                    WHERE id = %(id)s::uuid
                    RETURNING *
                    """,
                    {
                        "id": split_id,
                        "amount": amount,
                        "share_weight": share_weight,
                        "note": note,
                    },
                )
                row = cur.fetchone()
                if row:
                    retained_ids.append(split_id)
                    result_rows.append(row)
            else:
                cur.execute(
                    """
                    INSERT INTO transaction_splits (
                        transaction_id,
                        debtor_user_id,
                        amount,
                        share_weight,
                        note,
                        created_at,
                        updated_at,
                        deleted_at
                    )
                    VALUES (
                        %(transaction_id)s::uuid,
                        %(debtor_user_id)s::uuid,
                        %(amount)s,
                        %(share_weight)s,
                        %(note)s,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP,
                        NULL
                    )
                    RETURNING *
                    """,
                    {
                        "transaction_id": transaction_id,
                        "debtor_user_id": debtor_user_id,
                        "amount": amount,
                        "share_weight": share_weight,
                        "note": note,
                    },
                )
                row = cur.fetchone()
                if row:
                    split_id = row[0]
                    retained_ids.append(split_id)
                    result_rows.append(row)

        # Soft-delete any splits that are no longer present
        if existing_by_debtor:
            to_delete = [
                split_id
                for debtor, split_id in existing_by_debtor.items()
                if split_id not in retained_ids
            ]
            if to_delete:
                cur.execute(
                    """
                    UPDATE transaction_splits
                    SET deleted_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ANY(%(ids)s::uuid[])
                    """,
                    {"ids": to_delete},
                )

        # If payload is empty, ensure all existing splits are soft-deleted
        if not splits and existing_by_debtor:
            cur.execute(
                """
                UPDATE transaction_splits
                SET deleted_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE transaction_id = %(transaction_id)s::uuid
                  AND deleted_at IS NULL
                """,
                {"transaction_id": transaction_id},
            )

        conn.commit()

        # Map result rows to models
        return [row_to_model_with_cursor(r, TransactionSplit, cur) for r in result_rows]
    except Exception as exc:
        conn.rollback()
        logger.exception("Failed to replace splits for transaction %s", transaction_id)
        raise
    finally:
        cur.close()
        conn.close()


def list_friend_balances_for_user(user_id: str) -> List[FriendSplitBalance]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            WITH friend_balances AS (
                SELECT
                    CASE
                        WHEN t.original_payer_user_id = %(user_id)s::uuid THEN ts.debtor_user_id
                        ELSE t.original_payer_user_id
                    END AS friend_user_id,
                    SUM(
                        CASE WHEN t.original_payer_user_id = %(user_id)s::uuid THEN ts.amount ELSE 0 END
                    ) AS amount_owed_to_user,
                    SUM(
                        CASE WHEN ts.debtor_user_id = %(user_id)s::uuid THEN ts.amount ELSE 0 END
                    ) AS amount_user_owes
                FROM transaction_splits ts
                JOIN transactions t ON ts.transaction_id = t.id
                WHERE ts.deleted_at IS NULL
                  AND t.deleted_at IS NULL
                  AND (
                        t.original_payer_user_id = %(user_id)s::uuid
                        OR ts.debtor_user_id = %(user_id)s::uuid
                  )
                GROUP BY 1
            )
            SELECT friend_user_id, amount_owed_to_user, amount_user_owes
            FROM friend_balances
            WHERE friend_user_id IS NOT NULL AND friend_user_id <> %(user_id)s::uuid
            ORDER BY friend_user_id
            """,
            {"user_id": user_id},
        )
        rows = cur.fetchall()
        balances: List[FriendSplitBalance] = []
        for row in rows:
            friend_user_id, owed_to_user, user_owes = row
            balances.append(
                FriendSplitBalance(
                    friend_user_id=str(friend_user_id),
                    amount_owed_to_user=_decimal_to_float(owed_to_user),
                    amount_user_owes=_decimal_to_float(user_owes),
                )
            )
        return balances
    finally:
        cur.close()
        conn.close()


def list_splits_between_users(user_id: str, friend_user_id: str) -> List[SplitWithTransaction]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                ts.id,
                ts.transaction_id,
                ts.debtor_user_id,
                ts.amount,
                ts.share_weight,
                ts.note,
                ts.created_at,
                ts.updated_at,
                t.original_payer_user_id AS payer_user_id,
                t.amount AS transaction_amount,
                t.currency AS transaction_currency,
                t.type AS transaction_type,
                t.description AS transaction_description,
                t.merchant_name,
                t.category,
                t.authorized_date,
                t.posted_date
            FROM transaction_splits ts
            JOIN transactions t ON ts.transaction_id = t.id
            WHERE ts.deleted_at IS NULL
              AND t.deleted_at IS NULL
              AND (
                    (t.original_payer_user_id = %(user_id)s::uuid AND ts.debtor_user_id = %(friend_id)s::uuid)
                 OR (t.original_payer_user_id = %(friend_id)s::uuid AND ts.debtor_user_id = %(user_id)s::uuid)
              )
            ORDER BY t.posted_date DESC NULLS LAST, ts.created_at DESC
            """,
            {"user_id": user_id, "friend_id": friend_user_id},
        )
        rows = cur.fetchall()
        return [row_to_model_with_cursor(r, SplitWithTransaction, cur) for r in rows]
    finally:
        cur.close()
        conn.close()


def get_split_by_id(split_id: str) -> Optional[SplitWithTransaction]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                ts.id,
                ts.transaction_id,
                ts.debtor_user_id,
                ts.amount,
                ts.share_weight,
                ts.note,
                ts.created_at,
                ts.updated_at,
                t.original_payer_user_id AS payer_user_id,
                t.amount AS transaction_amount,
                t.currency AS transaction_currency,
                t.type AS transaction_type,
                t.description AS transaction_description,
                t.merchant_name,
                t.category,
                t.authorized_date,
                t.posted_date
            FROM transaction_splits ts
            JOIN transactions t ON ts.transaction_id = t.id
            WHERE ts.id = %(split_id)s::uuid
              AND ts.deleted_at IS NULL
              AND t.deleted_at IS NULL
            """,
            {"split_id": split_id},
        )
        row = cur.fetchone()
        return row_to_model_with_cursor(row, SplitWithTransaction, cur) if row else None
    finally:
        cur.close()
        conn.close()


def list_participants_for_transaction(transaction_id: str) -> List[TransactionSplit]:
    """Return splits (participants) including soft-deleted ones filtered out."""
    return list_splits_for_transaction(transaction_id)
