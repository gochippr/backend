import logging
from typing import List

from business.transaction import ingest_account_transactions
from database.supabase.account import (
    Account,
    create_account,
    get_accounts_by_user_id,
)
from database.supabase.user_plaid_items import UserPlaidItem, get_plaid_items_by_user_id
from integrations.plaid import PlaidAPIError, plaid_client
from models.auth_user import AuthUser
from models.plaid import Account as PlaidAccount

logger = logging.getLogger(__name__)


def get_user_accounts(auth_user: AuthUser) -> List[Account]:
    """
    Get all accounts for a user, syncing with Plaid data.

    This function:
    1. Gets all existing accounts from the database
    2. Gets all Plaid items for the user
    3. For each Plaid item, fetches accounts from Plaid
    4. Creates any accounts that exist in Plaid but not in the database
    5. Returns all accounts

    Args:
        auth_user: The authenticated user

    Returns:
        List of all accounts for the user
    """

    try:
        existing_accounts = get_accounts_by_user_id(auth_user.id)
        logger.info(
            f"Found {len(existing_accounts)} existing accounts for user {auth_user.id}"
        )
    except Exception as e:
        logger.error(f"Error fetching existing accounts for user {auth_user.id}: {e}")
        raise e

    try:
        plaid_items = get_plaid_items_by_user_id(auth_user.id)
        logger.info(f"Found {len(plaid_items)} Plaid items for user {auth_user.id}")
    except Exception as e:
        logger.error(f"Error fetching Plaid items for user {auth_user.id}: {e}")
        raise e

    if not plaid_items:
        return existing_accounts

    existing_external_ids = {
        acc.external_account_id for acc in existing_accounts if acc.external_account_id
    }

    for plaid_item in plaid_items:
        try:
            plaid_accounts = plaid_client.get_accounts(
                user_id=auth_user.id, item_id=plaid_item.item_id
            )
            logger.info(
                f"Fetched {len(plaid_accounts)} accounts from Plaid for item {plaid_item.item_id}"
            )

            _sync_plaid_items_accounts(
                user_id=auth_user.id,
                external_account_ids=existing_external_ids,
                plaid_item=plaid_item,
            )

        except PlaidAPIError as e:
            logger.error(
                f"Plaid API error for user {auth_user.id} on item {plaid_item.item_id}: {e}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error syncing accounts for user {auth_user.id} on item {plaid_item.item_id}: {e}"
            )
            continue

    # Re-fetch all accounts after syncing
    try:
        all_accounts = get_accounts_by_user_id(auth_user.id)
        logger.info(
            f"Total accounts after sync for user {auth_user.id}: {len(all_accounts)}"
        )
        return all_accounts
    except Exception as e:
        logger.error(f"Error re-fetching accounts for user {auth_user.id}: {e}")
        raise e


def _sync_plaid_items_accounts(
    user_id: str,
    external_account_ids: set[str],
    plaid_item: UserPlaidItem,
) -> None:
    plaid_accounts = plaid_client.get_accounts(
        user_id=str(plaid_item.user_id), item_id=plaid_item.item_id
    )

    for plaid_account in plaid_accounts:
        if plaid_account.account_id not in external_account_ids:
            _create_account_from_plaid(
                user_id=user_id,
                plaid_item=plaid_item,
                plaid_account=plaid_account,
            )


def _create_account_from_plaid(
    user_id: str,
    plaid_item: UserPlaidItem,
    plaid_account: PlaidAccount,
) -> Account:
    try:
        account = create_account(
            user_id=user_id,
            name=plaid_account.name,
            external_account_id=plaid_account.account_id,
            mask=plaid_account.mask,
            official_name=plaid_account.official_name,
            verification_status=plaid_account.verification_status,
            external_institution_id=plaid_item.institution_id,
            account_type="personal",
        )
        logger.info(f"Created account {account.id} for user {user_id}")
        ingest_account_transactions(account)

        return account
    except Exception as e:
        logger.error(
            f"Error creating account for user {user_id} with Plaid account {plaid_account.account_id}: {e}"
        )
        raise
