from __future__ import annotations

from datetime import date
from typing import Any, Optional


def map_plaid_account_to_db_fields(
    *,
    user_id: str,
    plaid_item_id: str,
    account: Any,
) -> dict[str, Any]:
    """Map a Plaid Account object (or compatible) to accounts table columns.

    Expected account fields: account_id, name, official_name, mask, type, subtype,
    balances.iso_currency_code, balances.current, balances.available.
    """
    balances = getattr(account, "balances", None)
    current = None
    available = None
    if balances is not None:
        current = getattr(balances, "current", None)
        available = getattr(balances, "available", None)

    return {
        "user_id": user_id,
        "plaid_item_id": plaid_item_id,
        "plaid_account_id": getattr(account, "account_id"),
        "name": getattr(account, "name", None),
        "official_name": getattr(account, "official_name", None),
        "mask": getattr(account, "mask", None),
        "type": getattr(account, "type", None),
        "subtype": getattr(account, "subtype", None),
        "current_balance": current,
        "available_balance": available,
    }


def _infer_tx_type(
    *, amount: float, personal_finance_primary: Optional[str], transaction_type: Optional[str]
) -> str:
    """Infer 'debit' vs 'credit' according to Plaid conventions.

    Rules (documented):
    - Store abs(amount) as amount.
    - For depository accounts, Plaid amount is positive for outflow; negative for inflow.
    - If ambiguous, fall back to personal_finance_category.primary (e.g., 'INCOME').
    - transaction_type/payment_channel may hint but is inconsistently present; we prefer amount sign.
    """
    # Primary rule: sign of amount (>= 0 => outflow => 'debit', < 0 => inflow => 'credit')
    if amount < 0:
        return "credit"
    if amount > 0:
        return "debit"
    # amount == 0.0, fallback on category
    if personal_finance_primary:
        primary = personal_finance_primary.upper()
        if "INCOME" in primary:
            return "credit"
    # Default to debit when unclear
    return "debit"


def map_plaid_transaction_to_db_fields(
    *,
    account_id: str,
    transaction: Any,
    account_owner_user_id: str,
) -> dict[str, Any]:
    """Map a Plaid Transaction object (or compatible) to transactions columns."""
    # Plaid amounts are positive for outflow; store absolute value
    raw_amount = float(getattr(transaction, "amount"))
    abs_amount = abs(raw_amount)

    # Optional helpers from Plaid transaction
    pfc = getattr(transaction, "personal_finance_category", None)
    pfc_primary: Optional[str] = getattr(pfc, "primary", None) if pfc else None
    tx_type_hint: Optional[str] = getattr(transaction, "transaction_type", None)

    tx_type = _infer_tx_type(
        amount=raw_amount, personal_finance_primary=pfc_primary, transaction_type=tx_type_hint
    )

    authorized_date: Optional[date] = getattr(transaction, "authorized_date", None)
    posted_date: Optional[date] = getattr(transaction, "date", None)

    return {
        "account_id": account_id,
        "external_txn_id": getattr(transaction, "transaction_id", None),
        "amount": abs_amount,
        "currency": getattr(transaction, "iso_currency_code", None),
        "type": tx_type,
        "merchant_name": getattr(transaction, "merchant_name", None),
        "description": getattr(transaction, "name", None),
        "category": None,
        "authorized_date": authorized_date,
        "posted_date": posted_date,
        "pending": bool(getattr(transaction, "pending", False)),
        "original_payer_user_id": account_owner_user_id,
    }
