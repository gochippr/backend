import logging
from fastapi import APIRouter, Depends, HTTPException

from database.supabase.account import list_accounts_for_user
from database.supabase.plaid_item import get_plaid_item_by_id
from models.account import AccountResponse, UserAccountsResponse
from models.auth_user import AuthUser
from utils.middlewares.auth_user import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/accounts")
async def get_user_accounts_endpoint(
    current_user: AuthUser = Depends(get_current_user),
) -> UserAccountsResponse:
    """
    Get all accounts for the current user.
    """
    logger.info(f"Getting accounts for user {current_user.id}")
    accounts = list_accounts_for_user(current_user.id)
    account_responses = []
    for account in accounts:
        # Map DB Account to API model, deriving external fields
        plaid_item = get_plaid_item_by_id(account.plaid_item_id)
        account_responses.append(
            AccountResponse(
                id=account.id,
                user_id=account.user_id,
                name=account.name or account.official_name or "",
                type=account.type or "personal",
                description=None,
                external_account_id=account.plaid_account_id,
                external_institution_id=plaid_item.institution_id
                if plaid_item
                else None,
                mask=account.mask,
                official_name=account.official_name,
                subtype=account.subtype,
                verification_status=None,
                is_active=True,
                created_at=account.created_at,
                updated_at=account.updated_at or account.created_at,
            )
        )

    return UserAccountsResponse(accounts=account_responses)
