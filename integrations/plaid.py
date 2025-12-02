import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import plaid
from cryptography.fernet import Fernet
from plaid.api import plaid_api
from plaid.configuration import Environment
from plaid.model.accounts_balance_get_request import (
    AccountsBalanceGetRequest,
)
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import (
    LinkTokenCreateRequestUser,
)
from plaid.model.products import Products
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_sync_request import (
    TransactionsSyncRequest,
)

from database.supabase.plaid_item import (
    create_or_update_plaid_item,
    deactivate_plaid_item,
    get_plaid_item_by_user_and_item,
)
from models.plaid import (
    Account,
    AccountBalance,
    DisconnectResponse,
    ItemStatus,
    ItemStatusError,
    ItemStatusResponse,
    SyncResponse,
    Transaction,
    TransactionLocation,
    TransactionsResponse,
)
from utils.constants import ENCRYPTION_KEY, PLAID_CLIENT_ID, PLAID_ENV, PLAID_SECRET

logger = logging.getLogger(__name__)


class PlaidError(Exception):
    """Base exception for Plaid integration errors"""

    pass


class PlaidConfigurationError(PlaidError):
    """Raised when Plaid configuration is missing or invalid"""

    pass


class PlaidTokenError(PlaidError):
    """Raised when token operations fail"""

    pass


class PlaidItemNotFoundError(PlaidError):
    """Raised when a Plaid item is not found"""

    pass


class PlaidAPIError(PlaidError):
    """Raised when Plaid API calls fail"""

    pass


class PlaidClient:
    """Plaid API client with encryption and error handling"""

    def __init__(self) -> None:
        self.client_id = PLAID_CLIENT_ID
        self.secret = PLAID_SECRET

        # Map environment string to Plaid Environment enum
        env_upper = PLAID_ENV.upper()
        if env_upper == "SANDBOX":
            self.env = Environment.Sandbox
        elif env_upper == "PRODUCTION":
            self.env = Environment.Production
        else:
            logger.warning(
                f"Unknown Plaid environment '{PLAID_ENV}', defaulting to Sandbox"
            )
            self.env = Environment.Sandbox

        if not all([self.client_id, self.secret]):
            raise PlaidConfigurationError(
                "Missing Plaid credentials in environment variables"
            )

        # Initialize Plaid client
        configuration = plaid.Configuration(
            host=self.env,
            api_key={
                "clientId": self.client_id,
                "secret": self.secret,
            },
        )

        api_client = plaid.ApiClient(configuration)
        self.plaid_client = plaid_api.PlaidApi(api_client)

        # Initialize encryption
        if not ENCRYPTION_KEY:
            raise PlaidConfigurationError("ENCRYPTION_KEY environment variable not set")

        self.fernet = Fernet(
            ENCRYPTION_KEY.encode()
            if isinstance(ENCRYPTION_KEY, str)
            else ENCRYPTION_KEY
        )

        logger.info(f"Plaid client initialized for environment: {PLAID_ENV}")

    def encrypt_token(self, token: str) -> str:
        """Encrypt access token before storing"""
        try:
            encrypted = self.fernet.encrypt(token.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Failed to encrypt token: {e}")
            raise PlaidTokenError(f"Token encryption failed: {e}")

    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt access token from storage"""
        try:
            decrypted = self.fernet.decrypt(encrypted_token.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt token: {e}")
            raise PlaidTokenError(f"Token decryption failed: {e}")

    def create_link_token(
        self, user_id: str, client_name: str = "Chippr"
    ) -> Dict[str, Any]:
        """Create a link token for Plaid Link initialization"""
        try:
            request = LinkTokenCreateRequest(
                products=[Products("auth"), Products("transactions")],
                client_name=client_name,
                country_codes=[CountryCode("US")],
                language="en",
                user=LinkTokenCreateRequestUser(client_user_id=user_id),
            )

            response = self.plaid_client.link_token_create(request)
            logger.info(f"Link token created for user: {user_id}")

            return {
                "link_token": response.link_token,
                "expiration": response.expiration.isoformat()
                if response.expiration
                else None,
            }

        except Exception as e:
            logger.error(f"Failed to create link token for user {user_id}: {e}")
            raise PlaidAPIError(f"Failed to create link token: {e}")

    def exchange_public_token(
        self,
        public_token: str,
        user_id: str,
        institution_id: Optional[str] = None,
        institution_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Exchange public token for access token and store in database"""
        try:
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self.plaid_client.item_public_token_exchange(request)

            access_token = response.access_token
            item_id = response.item_id

            # Encrypt access token before storing
            encrypted_token = self.encrypt_token(access_token)

            # Store in database (upsert)
            plaid_item = create_or_update_plaid_item(
                user_id=user_id,
                access_token=encrypted_token,
                item_id=item_id,
                institution_id=institution_id,
                institution_name=institution_name,
                is_active=True,
            )

            logger.info(
                f"Public token exchanged and stored for user {user_id}, item {item_id}"
            )

            return {
                "item_id": item_id,
                "access_token": access_token,  # Return unencrypted for immediate use
                "db_id": plaid_item.id,
            }

        except Exception as e:
            logger.error(f"Failed to exchange public token for user {user_id}: {e}")
            raise PlaidAPIError(f"Failed to exchange public token: {e}")

    def get_accounts(
        self, user_id: str, item_id: Optional[str] = None
    ) -> List[Account]:
        """Get accounts for user, optionally filtered by item_id"""
        try:
            # Get access token from database
            if item_id:
                # Get specific item's access token
                encrypted_token = self._get_encrypted_token(user_id, item_id)
            else:
                # Get all items for user (simplified - you might want to implement this)
                raise PlaidAPIError("item_id required for now")

            access_token = self.decrypt_token(encrypted_token)

            request = AccountsGetRequest(access_token=access_token)
            response = self.plaid_client.accounts_get(request)

            accounts = []
            for account in response.accounts:
                # Handle verification_status safely
                verification_status = None
                try:
                    if (
                        hasattr(account, "verification_status")
                        and account.verification_status
                    ):
                        verification_status = account.verification_status.value
                except AttributeError:
                    # verification_status field doesn't exist for this account type
                    pass

                accounts.append(
                    Account(
                        account_id=account.account_id,
                        balances=AccountBalance(
                            available=account.balances.available,
                            current=account.balances.current,
                            limit=account.balances.limit,
                            iso_currency_code=account.balances.iso_currency_code,
                            unofficial_currency_code=account.balances.unofficial_currency_code,
                        ),
                        mask=account.mask,
                        name=account.name,
                        official_name=account.official_name,
                        type=account.type.value,
                        subtype=account.subtype.value if account.subtype else None,
                        verification_status=verification_status,
                    )
                )

            logger.info(f"Retrieved {len(accounts)} accounts for user {user_id}")
            return accounts

        except Exception as e:
            logger.error(f"Failed to get accounts for user {user_id}: {e}")
            raise PlaidAPIError(f"Failed to retrieve accounts: {e}")

    def get_transactions(
        self,
        user_id: str,
        item_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        account_ids: Optional[List[str]] = None,
    ) -> TransactionsResponse:
        """Get transactions for user with optional date filtering"""
        try:
            encrypted_token = self._get_encrypted_token(user_id, item_id)
            access_token = self.decrypt_token(encrypted_token)

            # Default to last 30 days if no dates provided
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")

            # Convert string dates to date objects for Plaid API
            from datetime import date

            start_date_obj = date.fromisoformat(start_date)
            end_date_obj = date.fromisoformat(end_date)

            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date_obj,
                end_date=end_date_obj,
                options={"account_ids": account_ids} if account_ids else None,
            )

            response = self.plaid_client.transactions_get(request)

            transactions = []
            for transaction in response.transactions:
                # Handle location data safely
                location_data = None
                if transaction.location:
                    try:
                        location_data = TransactionLocation(
                            address=getattr(transaction.location, "address", None),
                            city=getattr(transaction.location, "city", None),
                            state=getattr(transaction.location, "state", None),
                            zip=getattr(transaction.location, "zip", None),
                            country=getattr(transaction.location, "country", None),
                            lat=getattr(transaction.location, "lat", None),
                            lon=getattr(transaction.location, "lon", None),
                        )
                    except AttributeError as e:
                        logger.warning(
                            f"Error processing location data for transaction {transaction.transaction_id}: {e}"
                        )
                        location_data = None

                transactions.append(
                    Transaction(
                        transaction_id=transaction.transaction_id,
                        account_id=transaction.account_id,
                        amount=transaction.amount,
                        date=transaction.date,
                        name=transaction.name,
                        merchant_name=transaction.merchant_name,
                        category=transaction.category,
                        category_id=transaction.category_id,
                        pending=transaction.pending,
                        location=location_data,
                    )
                )

            return TransactionsResponse(
                transactions=transactions,
                total_transactions=len(transactions),
                request_id=response.request_id,
            )

        except Exception as e:
            logger.error(f"Failed to get transactions for user {user_id}: {e}")
            raise PlaidAPIError(f"Failed to retrieve transactions: {e}")

    def sync_transactions(self, user_id: str, item_id: str) -> SyncResponse:
        """Manual sync for new transactions"""
        try:
            encrypted_token = self._get_encrypted_token(user_id, item_id)
            access_token = self.decrypt_token(encrypted_token)

            request = TransactionsSyncRequest(access_token=access_token)
            response = self.plaid_client.transactions_sync(request)

            logger.info(
                f"Transaction sync completed for user {user_id}, item {item_id}"
            )

            return SyncResponse(
                added=len(response.added),
                modified=len(response.modified),
                removed=len(response.removed),
                has_more=response.has_more,
                next_cursor=response.next_cursor,
                request_id=response.request_id,
            )

        except Exception as e:
            logger.error(f"Failed to sync transactions for user {user_id}: {e}")
            raise PlaidAPIError(f"Failed to sync transactions: {e}")

    def transactions_sync_page(
        self, user_id: str, item_id: str, cursor: Optional[str] = None
    ) -> tuple[list[object], list[object], list[object], Optional[str], bool]:
        """Fetch a single /transactions/sync page returning raw lists and cursor.

        Returns (added, modified, removed, next_cursor, has_more)
        """
        try:
            encrypted_token = self._get_encrypted_token(user_id, item_id)
            access_token = self.decrypt_token(encrypted_token)

            request_payload: dict[str, Any] = {"access_token": access_token}
            if cursor is not None:
                request_payload["cursor"] = cursor

            request = TransactionsSyncRequest(**request_payload)
            response = self.plaid_client.transactions_sync(request)

            return (
                list(response.added or []),
                list(response.modified or []),
                list(response.removed or []),
                response.next_cursor,
                bool(response.has_more),
            )
        except Exception as e:
            logger.error(
                f"Failed to sync transactions page for user {user_id}, item {item_id}: {e}"
            )
            raise PlaidAPIError(f"Failed to sync transactions page: {e}")

    def get_item_status(self, user_id: str, item_id: str) -> ItemStatusResponse:
        """Check item status and health"""
        try:
            encrypted_token = self._get_encrypted_token(user_id, item_id)
            access_token = self.decrypt_token(encrypted_token)

            request = ItemGetRequest(access_token=access_token)
            response = self.plaid_client.item_get(request)

            status = None
            if response.item.status:
                error = None
                if response.item.status.error:
                    error = ItemStatusError(
                        error_type=response.item.status.error.error_type,
                        error_code=response.item.status.error.error_code,
                        error_message=response.item.status.error.error_message,
                        display_message=response.item.status.error.display_message,
                        request_id=response.item.status.error.request_id,
                    )
                status = ItemStatus(
                    last_webhook=response.item.status.last_webhook,
                    error=error,
                )

            return ItemStatusResponse(
                item_id=response.item.item_id,
                institution_id=response.item.institution_id,
                status=status,
            )

        except Exception as e:
            logger.error(
                f"Failed to get item status for user {user_id}, item {item_id}: {e}"
            )
            raise PlaidAPIError(f"Failed to get item status: {e}")

    def get_balances(self, user_id: str, item_id: str) -> List[Account]:
        """Get current balances for all accounts"""
        try:
            encrypted_token = self._get_encrypted_token(user_id, item_id)
            access_token = self.decrypt_token(encrypted_token)

            request = AccountsBalanceGetRequest(access_token=access_token)
            response = self.plaid_client.accounts_balance_get(request)

            balances = []
            for account in response.accounts:
                balances.append(
                    Account(
                        account_id=account.account_id,
                        balances=AccountBalance(
                            available=account.balances.available,
                            current=account.balances.current,
                            limit=account.balances.limit,
                            iso_currency_code=account.balances.iso_currency_code,
                            unofficial_currency_code=account.balances.unofficial_currency_code,
                        ),
                        mask=account.mask,
                        name=account.name,
                        official_name=account.official_name,
                        type=account.type.value,
                        subtype=account.subtype.value if account.subtype else None,
                        verification_status=account.verification_status.value
                        if account.verification_status
                        else None,
                    )
                )

            logger.info(
                f"Retrieved balances for {len(balances)} accounts for user {user_id}"
            )
            return balances

        except Exception as e:
            logger.error(f"Failed to get balances for user {user_id}: {e}")
            raise PlaidAPIError(f"Failed to retrieve balances: {e}")

    def disconnect_item(self, user_id: str, item_id: str) -> DisconnectResponse:
        """Disconnect specific institution"""
        try:
            encrypted_token = self._get_encrypted_token(user_id, item_id)
            access_token = self.decrypt_token(encrypted_token)

            # Remove from Plaid
            request = ItemRemoveRequest(access_token=access_token)
            response = self.plaid_client.item_remove(request)

            # Soft delete from database
            item = get_plaid_item_by_user_and_item(user_id, item_id)
            if not item:
                raise PlaidItemNotFoundError("Item not found or access denied")
            deactivate_plaid_item(item.id)

            logger.info(f"Item {item_id} disconnected for user {user_id}")

            return DisconnectResponse(
                removed=response.removed, request_id=response.request_id
            )

        except Exception as e:
            logger.error(f"Failed to disconnect item {item_id} for user {user_id}: {e}")
            raise PlaidAPIError(f"Failed to disconnect item: {e}")

    def _get_encrypted_token(self, user_id: str, item_id: str) -> str:
        """Helper method to get encrypted token from database"""
        item = get_plaid_item_by_user_and_item(user_id, item_id)
        if not item:
            raise PlaidItemNotFoundError("Item not found or access denied")

        encrypted_token = item.access_token
        if not isinstance(encrypted_token, str):
            raise PlaidTokenError("Encrypted token is not a string")

        return encrypted_token


# Global Plaid client instance
plaid_client = PlaidClient()
