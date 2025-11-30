import logging

from fastapi import APIRouter, Depends, HTTPException

from business.account import get_user_accounts
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
    try:
        accounts = get_user_accounts(current_user)
        account_responses = [
            AccountResponse(
                id=account.id,
                user_id=account.user_id,
                name=account.name,
                type=account.type,
                description=account.description,
                external_account_id=account.external_account_id,
                external_institution_id=account.external_institution_id,
                mask=account.mask,
                official_name=account.official_name,
                subtype=account.subtype,
                verification_status=account.verification_status,
                is_active=account.is_active,
                created_at=account.created_at,
                updated_at=account.updated_at,
            )
            for account in accounts
        ]

        return UserAccountsResponse(accounts=account_responses)

    except Exception as e:
        logger.error(f"Error getting user accounts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user accounts")
