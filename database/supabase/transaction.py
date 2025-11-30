import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel

from database.supabase.orm import get_connection
from utils.database import row_to_model_with_cursor

logger = logging.getLogger(__name__)


class Transaction(BaseModel):
    id: UUID
    account_id: UUID
    category_id: Optional[UUID]
    description: str
    amount: Decimal
    transaction_date: date
    parent_transaction_id: Optional[UUID]
    external_transaction_id: Optional[str]
    external_reference: Optional[str]
    merchant_name: Optional[str]
    location_address: Optional[str]
    location_city: Optional[str]
    location_state: Optional[str]
    location_zip: Optional[str]
    location_country: Optional[str]
    location_lat: Optional[Decimal]
    location_lon: Optional[Decimal]
    pending: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


def get_account_transactions(
    account_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: Optional[int] = None,
) -> List[Transaction]:
    """
    Get transactions for an account with optional date filtering.

    Args:
        account_id: Account UUID
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Optional limit on number of transactions

    Returns:
        List of Transaction models
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        query = """
            SELECT * FROM transactions 
            WHERE account_id = %s
        """
        params: List[Any] = [str(account_id)]

        if start_date:
            query += " AND transaction_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND transaction_date <= %s"
            params.append(end_date)

        query += " ORDER BY transaction_date DESC, created_at DESC"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        cur.execute(query, params)
        results = cur.fetchall()
        return [row_to_model_with_cursor(row, Transaction, cur) for row in results]

    except Exception as e:
        logger.error(f"Error getting transactions for account {account_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def get_transaction_by_external_id(
    account_id: UUID, external_transaction_id: str
) -> Optional[Transaction]:
    """
    Get transaction by Plaid external transaction ID.

    Args:
        account_id: Account UUID
        external_transaction_id: Plaid transaction ID

    Returns:
        Transaction model or None if not found
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT * FROM transactions 
            WHERE account_id = %s AND external_transaction_id = %s
        """,
            (str(account_id), external_transaction_id),
        )

        result = cur.fetchone()
        return row_to_model_with_cursor(result, Transaction, cur) if result else None

    except Exception as e:
        logger.error(
            f"Error getting transaction by external ID {external_transaction_id}: {e}"
        )
        raise
    finally:
        cur.close()
        conn.close()


def create_transaction(
    account_id: UUID,
    description: str,
    amount: Decimal,
    transaction_date: date,
    category_id: Optional[UUID] = None,
    parent_transaction_id: Optional[UUID] = None,
    external_transaction_id: Optional[str] = None,
    external_reference: Optional[str] = None,
    merchant_name: Optional[str] = None,
    location_address: Optional[str] = None,
    location_city: Optional[str] = None,
    location_state: Optional[str] = None,
    location_zip: Optional[str] = None,
    location_country: Optional[str] = None,
    location_lat: Optional[Decimal] = None,
    location_lon: Optional[Decimal] = None,
    pending: bool = False,
    notes: Optional[str] = None,
) -> Transaction:
    """
    Create a new transaction.

    Args:
        account_id: Account UUID
        description: Transaction description
        amount: Transaction amount (positive=credit, negative=debit)
        transaction_date: Transaction date
        category_id: Optional category UUID
        parent_transaction_id: Optional parent transaction UUID
        external_transaction_id: Plaid transaction ID
        external_reference: External reference
        merchant_name: Merchant name
        location_address: Location address
        location_city: Location city
        location_state: Location state
        location_zip: Location zip
        location_country: Location country
        location_lat: Location latitude
        location_lon: Location longitude
        pending: Whether transaction is pending
        notes: Optional notes

    Returns:
        Created Transaction model
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO transactions (
                account_id, category_id, description, amount, transaction_date,
                parent_transaction_id, external_transaction_id, external_reference,
                merchant_name, location_address, location_city, location_state,
                location_zip, location_country, location_lat, location_lon,
                pending, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """,
            (
                str(account_id),
                str(category_id) if category_id else None,
                description,
                amount,
                transaction_date,
                str(parent_transaction_id) if parent_transaction_id else None,
                external_transaction_id,
                external_reference,
                merchant_name,
                location_address,
                location_city,
                location_state,
                location_zip,
                location_country,
                location_lat,
                location_lon,
                pending,
                notes,
            ),
        )

        result = cur.fetchone()
        conn.commit()
        return row_to_model_with_cursor(result, Transaction, cur)

    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating transaction for account {account_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def bulk_create_transactions(transactions: List[dict]) -> List[Transaction]:
    """
    Bulk create transactions.

    Args:
        transactions: List of transaction dictionaries

    Returns:
        List of created Transaction models
    """
    if not transactions:
        return []

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Prepare the INSERT statement
        insert_query = """
            INSERT INTO transactions (
                account_id, category_id, description, amount, transaction_date,
                parent_transaction_id, external_transaction_id, external_reference,
                merchant_name, location_address, location_city, location_state,
                location_zip, location_country, location_lat, location_lon,
                pending, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """

        created_transactions = []
        for transaction_data in transactions:
            cur.execute(
                insert_query,
                (
                    str(transaction_data["account_id"]),
                    str(transaction_data.get("category_id"))
                    if transaction_data.get("category_id")
                    else None,
                    transaction_data["description"],
                    transaction_data["amount"],
                    transaction_data["transaction_date"],
                    str(transaction_data.get("parent_transaction_id"))
                    if transaction_data.get("parent_transaction_id")
                    else None,
                    transaction_data.get("external_transaction_id"),
                    transaction_data.get("external_reference"),
                    transaction_data.get("merchant_name"),
                    transaction_data.get("location_address"),
                    transaction_data.get("location_city"),
                    transaction_data.get("location_state"),
                    transaction_data.get("location_zip"),
                    transaction_data.get("location_country"),
                    transaction_data.get("location_lat"),
                    transaction_data.get("location_lon"),
                    transaction_data.get("pending", False),
                    transaction_data.get("notes"),
                ),
            )

            result = cur.fetchone()
            created_transactions.append(
                row_to_model_with_cursor(result, Transaction, cur)
            )

        conn.commit()
        return created_transactions

    except Exception as e:
        conn.rollback()
        logger.error(f"Error bulk creating transactions: {e}")
        raise
    finally:
        cur.close()
        conn.close()
