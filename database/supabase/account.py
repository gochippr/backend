import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from database.supabase.orm import get_connection
from utils.database import row_to_model_with_cursor

logger = logging.getLogger(__name__)


class Account(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    type: str  # 'personal' or 'debt_ledger'
    description: Optional[str]
    external_account_id: Optional[str]  # Plaid account ID
    external_institution_id: Optional[str]  # Plaid institution ID
    mask: Optional[str]  # Last 4 digits of account
    official_name: Optional[str]
    subtype: Optional[str]  # Plaid account subtype
    verification_status: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


def get_accounts_by_user_id(user_id: str) -> List[Account]:
    """
    Get all accounts for a user.

    Args:
        user_id: User str

    Returns:
        List of Account models
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT * FROM accounts 
            WHERE user_id = %(user_id)s AND is_active = TRUE
            ORDER BY type DESC, name ASC
        """,
            {"user_id": user_id},
        )
        results = cur.fetchall()

    except Exception as e:
        logger.error(f"Error getting accounts for user {user_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()

    return [row_to_model_with_cursor(row, Account, cur) for row in results]


def create_account(
    user_id: str,
    name: str,
    account_type: str,
    description: Optional[str] = None,
    external_account_id: Optional[str] = None,
    external_institution_id: Optional[str] = None,
    mask: Optional[str] = None,
    official_name: Optional[str] = None,
    subtype: Optional[str] = None,
    verification_status: Optional[str] = None,
) -> Account:
    """
    Create a new account.

    Args:
        user_id: User UUID
        name: Account name
        account_type: 'personal' or 'debt_ledger'
        description: Account description
        external_account_id: Plaid account ID
        external_institution_id: Plaid institution ID
        mask: Last 4 digits of account
        official_name: Official account name
        subtype: Plaid account subtype
        verification_status: Account verification status

    Returns:
        Created Account model
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO accounts (
                user_id, name, type, description, external_account_id,
                external_institution_id, mask, official_name, subtype, verification_status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """,
            (
                user_id,
                name,
                account_type,
                description,
                external_account_id,
                external_institution_id,
                mask,
                official_name,
                subtype,
                verification_status,
            ),
        )

        result = cur.fetchone()
        conn.commit()

    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating account for user {user_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()

    return row_to_model_with_cursor(result, Account, cur)


def get_account_by_external_id(
    user_id: UUID, external_account_id: str
) -> Optional[Account]:
    """
    Get account by Plaid external account ID.

    Args:
        user_id: User UUID
        external_account_id: Plaid account ID

    Returns:
        Account model or None if not found
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT * FROM accounts 
            WHERE user_id = %s AND external_account_id = %s AND is_active = TRUE
        """,
            (str(user_id), external_account_id),
        )

        result = cur.fetchone()
        return row_to_model_with_cursor(result, Account, cur) if result else None

    except Exception as e:
        logger.error(f"Error getting account by external ID {external_account_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def create_debt_ledger_account(user_id: UUID) -> Account:
    """
    Create a debt ledger account for a user.

    Args:
        user_id: User UUID

    Returns:
        Created debt ledger Account model
    """
    return create_account(
        user_id=user_id,
        name="Debt Ledger",
        account_type="debt_ledger",
        description="Tracks money owed to/from other users",
    )
