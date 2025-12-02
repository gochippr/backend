import logging
from datetime import datetime
from typing import Optional

from psycopg2.extensions import connection as PGConnection
from pydantic import BaseModel

from utils.database import row_to_model_with_cursor

logger = logging.getLogger(__name__)


class PlaidItemSyncState(BaseModel):
    id: int
    plaid_item_id: str
    transactions_cursor: Optional[str]
    accounts_last_synced_at: Optional[datetime]
    updated_at: datetime


def get_or_create_sync_state(conn: PGConnection, plaid_item_id: str) -> PlaidItemSyncState:
    """Ensure a sync state row exists for the item and return it."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO plaid_item_sync_state (plaid_item_id)
        VALUES (%(plaid_item_id)s::uuid)
        ON CONFLICT (plaid_item_id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
        RETURNING id, plaid_item_id, transactions_cursor, accounts_last_synced_at, updated_at
        """,
        {"plaid_item_id": plaid_item_id},
    )
    row = cur.fetchone()
    return row_to_model_with_cursor(row, PlaidItemSyncState, cur)


def update_accounts_last_synced_at(conn: PGConnection, plaid_item_id: str) -> None:
    """Refresh the accounts_last_synced_at timestamp for the item."""
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE plaid_item_sync_state
        SET accounts_last_synced_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE plaid_item_id = %(plaid_item_id)s::uuid
        """,
        {"plaid_item_id": plaid_item_id},
    )


def update_sync_cursor(conn: PGConnection, plaid_item_id: str, next_cursor: Optional[str]) -> None:
    """Store the latest Plaid transactions cursor for the item."""
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE plaid_item_sync_state
        SET transactions_cursor = %(cursor)s, updated_at = CURRENT_TIMESTAMP
        WHERE plaid_item_id = %(plaid_item_id)s::uuid
        """,
        {"plaid_item_id": plaid_item_id, "cursor": next_cursor},
    )
