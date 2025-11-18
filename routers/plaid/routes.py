import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.supabase.dao.user_plaid_item import UserPlaidItemDAO
from integrations.plaid import (
    PlaidAPIError,
    PlaidConfigurationError,
    PlaidItemNotFoundError,
    PlaidTokenError,
    plaid_client,
)
from models.auth_user import AuthUser
from models.plaid import (
    AccountsResponse,
    BalancesResponse,
    CredentialsResponse,
    Institution,
    InstitutionsResponse,
    ItemStatusResponse,
    RefreshResponse,
    SearchResponse,
    SyncResponse,
    TransactionsResponse,
)
from utils.middlewares.auth_user import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plaid", tags=["Plaid Integration"])

def get_plaid_dao(db: AsyncSession = Depends(get_db)) -> UserPlaidItemDAO:
    return UserPlaidItemDAO(db)

# Request/Response Models
class LinkTokenRequest(BaseModel):
    client_name: Optional[str] = "Chippr"


class LinkTokenResponse(BaseModel):
    link_token: str
    expiration: Optional[str]


class PublicTokenExchangeRequest(BaseModel):
    public_token: str
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None


class PublicTokenExchangeResponse(BaseModel):
    item_id: str
    access_token: str
    db_id: int


class TransactionSearchRequest(BaseModel):
    query: str
    item_id: str


# Authentication & Setup Endpoints
@router.post("/create_link_token")
async def create_link_token(
    request: LinkTokenRequest, current_user: AuthUser = Depends(get_current_user)
) -> LinkTokenResponse:
    """Create link token for Plaid Link initialization"""
    try:
        result = plaid_client.create_link_token(
            user_id=current_user.id, client_name=current_user.name
        )
        return LinkTokenResponse(**result)
    except PlaidConfigurationError as e:
        logger.error(f"Plaid configuration error: {e}")
        raise HTTPException(status_code=500, detail="Plaid configuration error")
    except PlaidAPIError as e:
        logger.error(f"Plaid API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create link token")
    except Exception as e:
        logger.error(f"Unexpected error creating link token: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/exchange_public_token")
async def exchange_public_token(
    request: PublicTokenExchangeRequest,
    current_user: AuthUser = Depends(get_current_user),
    plaid_dao: UserPlaidItemDAO = Depends(get_plaid_dao),
) -> PublicTokenExchangeResponse:
    """Exchange public token for access token and store in DB"""
    try:
        result = await plaid_client.exchange_public_token(
            public_token=request.public_token,
            user_id=current_user.id,
            plaid_dao=plaid_dao,
            institution_id=request.institution_id,
            institution_name=request.institution_name,
        )
        return PublicTokenExchangeResponse(**result)
    except PlaidConfigurationError as e:
        logger.error(f"Plaid configuration error: {e}")
        raise HTTPException(status_code=500, detail="Plaid configuration error")
    except PlaidTokenError as e:
        logger.error(f"Plaid token error: {e}")
        raise HTTPException(status_code=500, detail="Token processing failed")
    except PlaidAPIError as e:
        logger.error(f"Plaid API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to exchange public token")
    except Exception as e:
        logger.error(f"Unexpected error exchanging token: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/check_credentials")
async def check_credentials() -> CredentialsResponse:
    """Health check for Plaid credentials"""
    try:
        # Simple check to verify Plaid client is properly initialized
        return CredentialsResponse(status="healthy", environment=str(plaid_client.env))
    except PlaidConfigurationError as e:
        logger.error(f"Plaid configuration error: {e}")
        raise HTTPException(status_code=500, detail="Plaid configuration error")
    except Exception as e:
        logger.error(f"Plaid credentials check failed: {e}")
        raise HTTPException(status_code=500, detail="Plaid credentials check failed")


# Account Management Endpoints
@router.get("/accounts")
async def get_accounts(
    item_id: str = Query(..., description="Plaid item ID"),
    current_user: AuthUser = Depends(get_current_user),
    plaid_dao: UserPlaidItemDAO = Depends(get_plaid_dao),
) -> AccountsResponse:
    """Get all accounts from connected institution"""
    try:
        accounts = await plaid_client.get_accounts(user_id=current_user.id, plaid_dao=plaid_dao, item_id=item_id)
        return AccountsResponse(accounts=accounts)
    except PlaidItemNotFoundError as e:
        logger.error(f"Item not found: {e}")
        raise HTTPException(status_code=404, detail="Item not found or access denied")
    except PlaidTokenError as e:
        logger.error(f"Token error: {e}")
        raise HTTPException(status_code=500, detail="Token processing failed")
    except PlaidAPIError as e:
        logger.error(f"Plaid API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve accounts")
    except Exception as e:
        logger.error(f"Unexpected error getting accounts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/accounts/{item_id}")
async def get_accounts_by_item(
    item_id: str, 
    current_user: AuthUser = Depends(get_current_user),
    plaid_dao: UserPlaidItemDAO = Depends(get_plaid_dao),
) -> AccountsResponse:
    """Get accounts for specific institution"""
    try:
        accounts = await plaid_client.get_accounts(user_id=current_user.id, plaid_dao=plaid_dao, item_id=item_id)
        return AccountsResponse(accounts=accounts)
    except PlaidItemNotFoundError as e:
        logger.error(f"Item not found: {e}")
        raise HTTPException(status_code=404, detail="Item not found or access denied")
    except PlaidTokenError as e:
        logger.error(f"Token error: {e}")
        raise HTTPException(status_code=500, detail="Token processing failed")
    except PlaidAPIError as e:
        logger.error(f"Plaid API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve accounts")
    except Exception as e:
        logger.error(f"Unexpected error getting accounts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/institutions")
async def get_institutions(
    current_user: AuthUser = Depends(get_current_user),
    plaid_dao: UserPlaidItemDAO = Depends(get_plaid_dao),
) -> InstitutionsResponse:
    """Get list of connected institutions"""
    try:
        logger.info(f"Fetching institutions for user {current_user.id}")
        institutions = await plaid_dao.get_user_items(current_user.id)
        # Convert UserPlaidItem to Institution model
        institution_models = []
        for item in institutions:
            institution_models.append(Institution(
                id=getattr(item, 'id'),
                user_id=getattr(item, 'user_id'), 
                item_id=getattr(item, 'item_id'),
                institution_id=getattr(item, 'institution_id'),
                institution_name=getattr(item, 'institution_name'),
                created_at=getattr(item, 'created_at').isoformat(),
                updated_at=getattr(item, 'updated_at').isoformat(), 
                delete_at=getattr(item, 'delete_at').isoformat() if getattr(item, 'delete_at') else None,
                is_active=getattr(item, 'is_active'),
            ))
            logger.info(f"Institution {getattr(item, 'delete_at')} created")
        return InstitutionsResponse(institutions=institution_models)
    except Exception as e:
        logger.error(f"Failed to get institutions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve institutions")


@router.post("/disconnect/{item_id}")
async def disconnect_institution(
    item_id: str, 
    current_user: AuthUser = Depends(get_current_user),
    plaid_dao: UserPlaidItemDAO = Depends(get_plaid_dao),
) -> None:
    """Disconnect specific institution"""
    try:
        await plaid_client.disconnect_item(user_id=current_user.id, item_id=item_id, plaid_dao=plaid_dao)
        return
    except PlaidItemNotFoundError as e:
        logger.error(f"Item not found: {e}")
        raise HTTPException(status_code=404, detail="Item not found or access denied")
    except PlaidTokenError as e:
        logger.error(f"Token error: {e}")
        raise HTTPException(status_code=500, detail="Token processing failed")
    except PlaidAPIError as e:
        logger.error(f"Plaid API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect institution")
    except Exception as e:
        logger.error(f"Unexpected error disconnecting item: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Transaction Endpoints
@router.get("/transactions")
async def get_transactions(
    item_id: str = Query(..., description="Plaid item ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    account_ids: Optional[List[str]] = Query(None, description="Filter by account IDs"),
    current_user: AuthUser = Depends(get_current_user),
    plaid_dao: UserPlaidItemDAO = Depends(get_plaid_dao),
) -> TransactionsResponse:
    """Get transactions from all accounts with date filtering"""
    try:
        result = await plaid_client.get_transactions(
            user_id=current_user.id,
            item_id=item_id,
            plaid_dao=plaid_dao,
            start_date=start_date,
            end_date=end_date,
            account_ids=account_ids,
        )
        return result
    except PlaidItemNotFoundError as e:
        logger.error(f"Item not found: {e}")
        raise HTTPException(status_code=404, detail="Item not found or access denied")
    except PlaidTokenError as e:
        logger.error(f"Token error: {e}")
        raise HTTPException(status_code=500, detail="Token processing failed")
    except PlaidAPIError as e:
        logger.error(f"Plaid API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve transactions")
    except Exception as e:
        logger.error(f"Unexpected error getting transactions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/transactions/{account_id}")
async def get_transactions_by_account(
    account_id: str,
    item_id: str = Query(..., description="Plaid item ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: AuthUser = Depends(get_current_user),
    plaid_dao: UserPlaidItemDAO = Depends(get_plaid_dao),
) -> TransactionsResponse:
    """Get transactions for specific account"""
    try:
        result = await plaid_client.get_transactions(
            user_id=current_user.id,
            item_id=item_id,
            plaid_dao=plaid_dao,
            start_date=start_date,
            end_date=end_date,
            account_ids=[account_id],
        )
        return result
    except PlaidItemNotFoundError as e:
        logger.error(f"Item not found: {e}")
        raise HTTPException(status_code=404, detail="Item not found or access denied")
    except PlaidTokenError as e:
        logger.error(f"Token error: {e}")
        raise HTTPException(status_code=500, detail="Token processing failed")
    except PlaidAPIError as e:
        logger.error(f"Plaid API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve transactions")
    except Exception as e:
        logger.error(f"Unexpected error getting transactions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/transactions/sync")
async def sync_transactions(
    item_id: str = Query(..., description="Plaid item ID"),
    current_user: AuthUser = Depends(get_current_user),
    plaid_dao: UserPlaidItemDAO = Depends(get_plaid_dao),
) -> SyncResponse:
    """Manual sync for new transactions"""
    try:
        result = await plaid_client.sync_transactions(
            user_id=current_user.id, item_id=item_id, plaid_dao=plaid_dao
        )
        return result
    except PlaidItemNotFoundError as e:
        logger.error(f"Item not found: {e}")
        raise HTTPException(status_code=404, detail="Item not found or access denied")
    except PlaidTokenError as e:
        logger.error(f"Token error: {e}")
        raise HTTPException(status_code=500, detail="Token processing failed")
    except PlaidAPIError as e:
        logger.error(f"Plaid API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync transactions")
    except Exception as e:
        logger.error(f"Unexpected error syncing transactions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/transactions/search")
async def search_transactions(
    query: str = Query(..., description="Search query"),
    item_id: str = Query(..., description="Plaid item ID"),
    current_user: AuthUser = Depends(get_current_user),
) -> SearchResponse:
    """Search transactions by query"""
    try:
        # This would need to be implemented with proper search logic
        # For now, return a placeholder
        return SearchResponse(
            transactions=[],
            query=query,
            message="Search functionality not implemented yet",
        )
    except Exception as e:
        logger.error(f"Failed to search transactions: {e}")
        raise HTTPException(status_code=500, detail="Failed to search transactions")


# Item Management & Error Handling
@router.get("/item/{item_id}/status")
async def get_item_status(
    item_id: str, 
    current_user: AuthUser = Depends(get_current_user),
    plaid_dao: UserPlaidItemDAO = Depends(get_plaid_dao),
) -> ItemStatusResponse:
    """Check item status and health"""
    try:
        status = await plaid_client.get_item_status(user_id=current_user.id, item_id=item_id, plaid_dao=plaid_dao)
        return status
    except PlaidItemNotFoundError as e:
        logger.error(f"Item not found: {e}")
        raise HTTPException(status_code=404, detail="Item not found or access denied")
    except PlaidTokenError as e:
        logger.error(f"Token error: {e}")
        raise HTTPException(status_code=500, detail="Token processing failed")
    except PlaidAPIError as e:
        logger.error(f"Plaid API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get item status")
    except Exception as e:
        logger.error(f"Unexpected error getting item status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/item/{item_id}/refresh")
async def refresh_item(
    item_id: str, current_user: AuthUser = Depends(get_current_user)
) -> RefreshResponse:
    """Force refresh item data"""
    try:
        # This would trigger a manual refresh of the item
        # For now, return a placeholder
        return RefreshResponse(
            success=True,
            item_id=item_id,
            message="Refresh functionality not implemented yet",
        )
    except Exception as e:
        logger.error(f"Failed to refresh item {item_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh item")


@router.get("/balances")
async def get_balances(
    item_id: str = Query(..., description="Plaid item ID"),
    current_user: AuthUser = Depends(get_current_user),
    plaid_dao: UserPlaidItemDAO = Depends(get_plaid_dao),
) -> BalancesResponse:
    """Get current balances for all accounts"""
    try:
        balances = await plaid_client.get_balances(user_id=current_user.id, item_id=item_id, plaid_dao=plaid_dao)
        return BalancesResponse(balances=balances)
    except PlaidItemNotFoundError as e:
        logger.error(f"Item not found: {e}")
        raise HTTPException(status_code=404, detail="Item not found or access denied")
    except PlaidTokenError as e:
        logger.error(f"Token error: {e}")
        raise HTTPException(status_code=500, detail="Token processing failed")
    except PlaidAPIError as e:
        logger.error(f"Plaid API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve balances")
    except Exception as e:
        logger.error(f"Unexpected error getting balances: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
