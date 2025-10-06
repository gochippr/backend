import logging
from fastapi import APIRouter, Depends

from database.supabase.account import list_accounts_for_user
from database.supabase.balance import get_friend_balances_for_user
from database.supabase.plaid_item import get_plaid_item_by_id
from models.account import AccountResponse, UserAccountsResponse, UserBalanceResponse
from models.auth_user import AuthUser
from utils.middlewares.auth_user import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("", response_model=UserAccountsResponse)
async def get_accounts(
    current_user: AuthUser = Depends(get_current_user),
) -> UserAccountsResponse:
    """Return the current user's accounts (possibly empty)."""
    logger.info("Getting accounts for user %s", current_user.id)
    accounts = list_accounts_for_user(current_user.id)

    account_responses: list[AccountResponse] = []
    for account in accounts:
        plaid_item = get_plaid_item_by_id(account.plaid_item_id)
        account_responses.append(
            AccountResponse(
                id=account.id,
                user_id=account.user_id,
                name=account.name or account.official_name or "",
                type=account.type or "personal",
                description=None,
                external_account_id=account.plaid_account_id,
                external_institution_id=plaid_item.institution_id if plaid_item else None,
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


@router.get("/balance", response_model=UserBalanceResponse)
async def get_account_balances(
    current_user: AuthUser = Depends(get_current_user),
) -> UserBalanceResponse:
    """Return aggregated balances including friend credits and debts."""
    accounts = list_accounts_for_user(current_user.id)
    total_balance = sum((account.current_balance or 0.0) for account in accounts)

    friend_credit, friend_debt = get_friend_balances_for_user(current_user.id)
    real_credit_available = total_balance + friend_credit - friend_debt

    return UserBalanceResponse(
        total_balance=total_balance,
        friend_credit=friend_credit,
        friend_debt=friend_debt,
        real_credit_available=real_credit_available,
    )
