import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from database.supabase.account import Account
from database.supabase.transaction import (
    create_transaction,
    get_account_transactions,
)
from database.supabase.user_plaid_items import UserPlaidItem, get_plaid_items_by_user_id
from integrations.plaid import PlaidAPIError, plaid_client
from models.plaid import Transaction as PlaidTransaction

logger = logging.getLogger(__name__)


def ingest_account_transactions(account: Account) -> None:
    """
    Ingest transactions for an account from Plaid.

    This function:
    1. Validates the account has required external identifiers
    2. Finds the corresponding Plaid item for the account
    3. Fetches transactions from Plaid for this account
    4. Gets existing transactions from the database
    5. Creates any missing transactions

    Args:
        account: The account to ingest transactions for
    """
    if not _validate_account_for_ingestion(account):
        return

    logger.info(f"Starting transaction ingestion for account {account.id}")

    try:
        plaid_item = _find_plaid_item_for_account(account)
        if not plaid_item:
            return

        plaid_transactions = _fetch_plaid_transactions(account, plaid_item)
        existing_external_ids = _get_existing_transaction_ids(account)

        new_transactions_created = _create_missing_transactions(
            account, plaid_transactions, existing_external_ids
        )

        logger.info(
            f"Created {new_transactions_created} new transactions for account {account.id}"
        )

    except PlaidAPIError as e:
        logger.error(
            f"Plaid API error during transaction ingestion for account {account.id}: {e}"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error during transaction ingestion for account {account.id}: {e}"
        )


def _validate_account_for_ingestion(account: Account) -> bool:
    """
    Validate that the account has the required fields for transaction ingestion.

    Args:
        account: The account to validate

    Returns:
        True if account is valid for ingestion, False otherwise
    """
    if not account.external_account_id:
        logger.info(
            f"Account {account.id} has no external_account_id, skipping transaction ingestion"
        )
        return False

    if not account.external_institution_id:
        logger.info(
            f"Account {account.id} has no external_institution_id, skipping transaction ingestion"
        )
        return False

    return True


def _find_plaid_item_for_account(account: Account) -> Optional[UserPlaidItem]:
    """
    Find the Plaid item that corresponds to the given account.

    Args:
        account: The account to find the Plaid item for

    Returns:
        The matching UserPlaidItem or None if not found
    """
    try:
        plaid_items = get_plaid_items_by_user_id(str(account.user_id))

        for item in plaid_items:
            if item.institution_id == account.external_institution_id:
                return item

        logger.error(
            f"Could not find Plaid item for account {account.id} "
            f"with institution_id {account.external_institution_id}"
        )
        return None

    except Exception as e:
        logger.error(f"Error fetching Plaid items for account {account.id}: {e}")
        return None


def _fetch_plaid_transactions(
    account: Account, plaid_item: UserPlaidItem
) -> List[PlaidTransaction]:
    """
    Fetch transactions from Plaid for the given account.

    Args:
        account: The account to fetch transactions for
        plaid_item: The Plaid item containing access credentials

    Returns:
        List of Plaid transactions
    """
    # Get transactions from Plaid for this account (last 30 days)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    transactions_response = plaid_client.get_transactions(
        user_id=str(account.user_id),
        item_id=plaid_item.item_id,
        start_date=start_date,
        end_date=end_date,
        account_ids=[account.external_account_id]
        if account.external_account_id
        else None,
    )

    logger.info(
        f"Retrieved {len(transactions_response.transactions)} transactions "
        f"from Plaid for account {account.id}"
    )

    return transactions_response.transactions


def _get_existing_transaction_ids(account: Account) -> set[str]:
    """
    Get the set of existing external transaction IDs for the account.

    Args:
        account: The account to get existing transaction IDs for

    Returns:
        Set of external transaction IDs that already exist in the database
    """
    existing_transactions = get_account_transactions(account.id)
    return {
        txn.external_transaction_id
        for txn in existing_transactions
        if txn.external_transaction_id
    }


def _create_missing_transactions(
    account: Account,
    plaid_transactions: List[PlaidTransaction],
    existing_external_ids: set[str],
) -> int:
    """
    Create transactions that exist in Plaid but not in our database.

    Args:
        account: The account to create transactions for
        plaid_transactions: List of transactions from Plaid
        existing_external_ids: Set of transaction IDs that already exist

    Returns:
        Number of new transactions created
    """
    new_transactions_created = 0

    for plaid_txn in plaid_transactions:
        if plaid_txn.transaction_id not in existing_external_ids:
            if _create_transaction_from_plaid(account, plaid_txn):
                new_transactions_created += 1
                existing_external_ids.add(plaid_txn.transaction_id)

    return new_transactions_created


def _create_transaction_from_plaid(
    account: Account, plaid_txn: PlaidTransaction
) -> bool:
    """
    Create a single transaction from Plaid transaction data.

    Args:
        account: The account to create the transaction for
        plaid_txn: The Plaid transaction data

    Returns:
        True if transaction was created successfully, False otherwise
    """
    try:
        # Convert Plaid transaction data to our format
        amount = _convert_plaid_amount(plaid_txn.amount)
        transaction_date = plaid_txn.date
        location_data = _extract_location_data(plaid_txn)

        # Create transaction
        create_transaction(
            account_id=account.id,
            description=plaid_txn.name,
            amount=amount,
            transaction_date=transaction_date,
            external_transaction_id=plaid_txn.transaction_id,
            merchant_name=plaid_txn.merchant_name,
            pending=plaid_txn.pending,
            **location_data,
        )

        return True

    except Exception as e:
        logger.error(
            f"Error creating transaction {plaid_txn.transaction_id} "
            f"for account {account.id}: {e}"
        )
        return False


def _convert_plaid_amount(plaid_amount: float) -> Decimal:
    """
    Convert Plaid amount to our system's format.

    Plaid amounts are positive for debits (money going out).
    Our system uses negative for debits, positive for credits.

    Args:
        plaid_amount: The amount from Plaid

    Returns:
        Converted decimal amount
    """
    return Decimal(str(-plaid_amount))


def _extract_location_data(plaid_txn: PlaidTransaction) -> dict:
    """
    Extract location data from a Plaid transaction.

    Args:
        plaid_txn: The Plaid transaction

    Returns:
        Dictionary containing location data fields
    """
    location_data: dict = {
        "location_address": None,
        "location_city": None,
        "location_state": None,
        "location_zip": None,
        "location_country": None,
        "location_lat": None,
        "location_lon": None,
    }

    if plaid_txn.location:
        location_data["location_address"] = plaid_txn.location.address
        location_data["location_city"] = plaid_txn.location.city
        location_data["location_state"] = plaid_txn.location.state
        location_data["location_zip"] = plaid_txn.location.zip
        location_data["location_country"] = plaid_txn.location.country
        location_data["location_lat"] = (
            Decimal(str(plaid_txn.location.lat)) if plaid_txn.location.lat else None
        )
        location_data["location_lon"] = (
            Decimal(str(plaid_txn.location.lon)) if plaid_txn.location.lon else None
        )

    return location_data
