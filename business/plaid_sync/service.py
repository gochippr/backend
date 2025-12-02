from __future__ import annotations

import json
import logging
from typing import List, Optional

from integrations.plaid import PlaidAPIError, PlaidClient

from business.plaid_sync import mappers
from business.plaid_sync.models import ItemRow, SyncSummary
from database.supabase import account as account_repo
from database.supabase import plaid_item as plaid_item_repo
from database.supabase import plaid_item_sync_state as sync_state_repo
from database.supabase import transaction as transaction_repo
from database.supabase.orm import get_connection

logger = logging.getLogger(__name__)


async def sync_item(
    *,
    plaid_client: PlaidClient,
    item_db_id: str,
    item_external_id: str,
    user_id: str,
) -> SyncSummary:
    accounts_upserted = 0
    tx_added = 0
    tx_modified = 0
    tx_removed = 0
    last_has_more = False

    # 1) Sync accounts
    try:
        accounts = plaid_client.get_accounts(user_id=user_id, item_id=item_external_id)
    except Exception as e:  # Surface as item-level error
        logger.error(
            json.dumps(
                {
                    "event": "plaid_sync.accounts_get_failed",
                    "item_id": item_external_id,
                    "error": str(e),
                }
            )
        )
        return SyncSummary(
            plaid_item_id=item_external_id,
            accounts_upserted=0,
            tx_added=0,
            tx_modified=0,
            tx_removed=0,
            has_more=False,
            error_code="accounts_get_failed",
            error_message=str(e),
        )

    # Upsert accounts within one transaction
    conn = get_connection()
    try:
        sync_state_repo.get_or_create_sync_state(conn, item_db_id)
        for acct in accounts:
            data = mappers.map_plaid_account_to_db_fields(
                user_id=user_id, plaid_item_id=item_db_id, account=acct
            )
            account_repo.upsert_plaid_account(conn, **data)
            accounts_upserted += 1
        sync_state_repo.update_accounts_last_synced_at(conn, item_db_id)
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(
            json.dumps(
                {
                    "event": "plaid_sync.accounts_upsert_failed",
                    "item_id": item_external_id,
                    "error": str(e),
                }
            )
        )
        return SyncSummary(
            plaid_item_id=item_external_id,
            accounts_upserted=accounts_upserted,
            tx_added=0,
            tx_modified=0,
            tx_removed=0,
            has_more=False,
            error_code="accounts_upsert_failed",
            error_message=str(e),
        )
    finally:
        conn.close()

    # 2) Transactions delta sync loop
    next_cursor: Optional[str] = None
    # Load cursor
    conn0 = get_connection()
    try:
        state = sync_state_repo.get_or_create_sync_state(conn0, item_db_id)
        next_cursor = state.transactions_cursor
        conn0.commit()
    except Exception:
        conn0.rollback()
        raise
    finally:
        conn0.close()

    page = 0
    while True:
        page += 1
        try:
            (
                added,
                modified,
                removed,
                next_cursor_out,
                has_more,
            ) = plaid_client.transactions_sync_page(
                user_id=user_id, item_id=item_external_id, cursor=next_cursor
            )
        except PlaidAPIError as e:
            # Continue other items: return summary with error attached
            logger.error(
                json.dumps(
                    {
                        "event": "plaid_sync.transactions_sync_failed",
                        "item_id": item_external_id,
                        "cursor": next_cursor,
                        "error": str(e),
                    }
                )
            )
            return SyncSummary(
                plaid_item_id=item_external_id,
                accounts_upserted=accounts_upserted,
                tx_added=tx_added,
                tx_modified=tx_modified,
                tx_removed=tx_removed,
                has_more=last_has_more,
                error_code="transactions_sync_failed",
                error_message=str(e),
            )

        # Process one page within a short DB transaction boundary
        connp = get_connection()
        try:
            # Ensure accounts exist (already upserted) and map new transactions
            for t in added:
                plaid_account_id = getattr(t, "account_id")
                account_id = account_repo.get_account_id_by_plaid_account_id(
                    connp,
                    user_id=user_id,
                    plaid_item_id=item_db_id,
                    plaid_account_id=plaid_account_id,
                )
                if not account_id:
                    # Skip if account not found or not owned by user
                    continue

                # Pending → posted reconciliation
                pending_id = getattr(t, "pending_transaction_id", None)
                posted_id = getattr(t, "transaction_id", None)
                tx_data = mappers.map_plaid_transaction_to_db_fields(
                    account_id=account_id, transaction=t, account_owner_user_id=user_id
                )
                if pending_id and posted_id:
                    relinked = transaction_repo.relink_pending_to_posted(
                        connp,
                        pending_transaction_id=pending_id,
                        posted_transaction_id=posted_id,
                        posted_data=tx_data,
                    )
                    if relinked:
                        tx_modified += 1
                        continue

                transaction_repo.upsert_transaction_added(connp, data=tx_data)
                tx_added += 1

            for t in modified:
                # Update mutable fields on existing record
                tx_data = mappers.map_plaid_transaction_to_db_fields(
                    account_id="",  # account_id immutable here; ignored in update
                    transaction=t,
                    account_owner_user_id=user_id,
                )
                tx_data["external_txn_id"] = getattr(t, "transaction_id", None)
                transaction_repo.apply_transaction_modified(connp, data=tx_data)
                tx_modified += 1

            # Removed: soft-delete by external id, scoped to user
            removed_ids = [getattr(r, "transaction_id") for r in removed]
            transaction_repo.apply_transaction_removed(
                connp, user_id=user_id, external_txn_ids=removed_ids
            )
            tx_removed += len(removed_ids)

            # Persist cursor for the item
            sync_state_repo.update_sync_cursor(connp, item_db_id, next_cursor_out)
            last_has_more = has_more
            connp.commit()
        except Exception as e:
            connp.rollback()
            logger.error(
                json.dumps(
                    {
                        "event": "plaid_sync.page_processing_failed",
                        "item_id": item_external_id,
                        "page": page,
                        "error": str(e),
                    }
                )
            )
            return SyncSummary(
                plaid_item_id=item_external_id,
                accounts_upserted=accounts_upserted,
                tx_added=tx_added,
                tx_modified=tx_modified,
                tx_removed=tx_removed,
                has_more=last_has_more,
                error_code="page_processing_failed",
                error_message=str(e),
            )
        finally:
            connp.close()

        next_cursor = next_cursor_out
        if not last_has_more:
            break

    return SyncSummary(
        plaid_item_id=item_external_id,
        accounts_upserted=accounts_upserted,
        tx_added=tx_added,
        tx_modified=tx_modified,
        tx_removed=tx_removed,
        has_more=last_has_more,
    )


async def sync_all_items_for_user(
    *, plaid_client: PlaidClient, user_id: str
) -> list[SyncSummary]:
    """Fetch active items for user and sync each sequentially.

    Kept sequential for simplicity/rate-limits; can be parallelized cautiously.
    """
    conn = get_connection()
    try:
        plaid_items = plaid_item_repo.list_active_plaid_items_for_user(conn, user_id)
        items: List[ItemRow] = [
            ItemRow(id=item.id, user_id=item.user_id, item_id=item.item_id)
            for item in plaid_items
        ]
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    results: list[SyncSummary] = []
    for item in items:
        summary = await sync_item(
            plaid_client=plaid_client,
            item_db_id=item.id,
            item_external_id=item.item_id,
            user_id=user_id,
        )
        results.append(summary)
    return results
