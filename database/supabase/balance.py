from __future__ import annotations

import logging
from decimal import Decimal
from typing import Tuple

from database.supabase.orm import get_connection

logger = logging.getLogger(__name__)


def _decimal_to_float(value: Decimal | None) -> float:
    return float(value) if value is not None else 0.0


def get_friend_balances_for_user(user_id: str) -> Tuple[float, float]:
    """Return (credit, debt) amounts for the user's friend ledger."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN t.original_payer_user_id = %(user_id)s::uuid THEN ts.amount ELSE 0 END), 0) AS owed_to_user,
                COALESCE(SUM(CASE WHEN ts.debtor_user_id = %(user_id)s::uuid THEN ts.amount ELSE 0 END), 0) AS user_owes
            FROM transaction_splits ts
            JOIN transactions t ON ts.transaction_id = t.id
            WHERE ts.deleted_at IS NULL
              AND t.deleted_at IS NULL
              AND (
                    t.original_payer_user_id = %(user_id)s::uuid
                    OR ts.debtor_user_id = %(user_id)s::uuid
              )
            """,
            {"user_id": user_id},
        )
        owed_to_user, user_owes = cur.fetchone() or (Decimal(0), Decimal(0))

        cur.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN s.to_user_id = %(user_id)s::uuid THEN s.amount ELSE 0 END), 0) AS settlements_received,
                COALESCE(SUM(CASE WHEN s.from_user_id = %(user_id)s::uuid THEN s.amount ELSE 0 END), 0) AS settlements_paid
            FROM settlements s
            WHERE s.deleted_at IS NULL
              AND (
                    s.to_user_id = %(user_id)s::uuid
                    OR s.from_user_id = %(user_id)s::uuid
              )
            """,
            {"user_id": user_id},
        )
        settlements_received, settlements_paid = cur.fetchone() or (Decimal(0), Decimal(0))

        credit = _decimal_to_float(owed_to_user) - _decimal_to_float(settlements_received)
        debt = _decimal_to_float(user_owes) - _decimal_to_float(settlements_paid)

        return max(credit, 0.0), max(debt, 0.0)
    except Exception:
        logger.exception("Failed computing friend balances for user %s", user_id)
        raise
    finally:
        cur.close()
        conn.close()

