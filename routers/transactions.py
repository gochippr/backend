import logging
from datetime import date, timedelta
from typing import Iterable, List

from fastapi import APIRouter, Depends

from database.supabase.transaction import (
    get_spending_by_category_for_user,
    list_transactions_for_user,
)
from models.auth_user import AuthUser
from models.transaction import (
    TransactionCategorySummary,
    TransactionResponse,
    TransactionSummaryResponse,
    UserTransactionsResponse,
)
from utils.middlewares.auth_user import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["Transactions"])


def _previous_month_period(reference: date) -> tuple[date, date, date]:
    """Return start, end (inclusive), and end-exclusive dates for the previous month."""
    first_day_this_month = reference.replace(day=1)
    last_day_previous_month = first_day_this_month - timedelta(days=1)
    first_day_previous_month = last_day_previous_month.replace(day=1)
    end_exclusive = last_day_previous_month + timedelta(days=1)
    return first_day_previous_month, last_day_previous_month, end_exclusive


def _to_transaction_response_list(
    transactions: Iterable,
) -> List[TransactionResponse]:
    responses: List[TransactionResponse] = []
    for txn in transactions:
        data = txn.model_dump() if hasattr(txn, "model_dump") else txn.dict()
        responses.append(TransactionResponse(**data))
    return responses


@router.get("", response_model=UserTransactionsResponse)
async def get_user_transactions(
    current_user: AuthUser = Depends(get_current_user),
) -> UserTransactionsResponse:
    """Return transactions for the authenticated user sorted from newest to oldest."""
    transactions = list_transactions_for_user(current_user.id)
    logger.info("Fetched %s transactions for user %s", len(transactions), current_user.id)
    return UserTransactionsResponse(transactions=_to_transaction_response_list(transactions))


@router.get("/summary", response_model=TransactionSummaryResponse)
async def get_last_month_summary(
    current_user: AuthUser = Depends(get_current_user),
) -> TransactionSummaryResponse:
    """Return spending summary for the most recently completed calendar month."""
    period_start, period_end, period_end_exclusive = _previous_month_period(date.today())

    category_totals = get_spending_by_category_for_user(
        current_user.id,
        start_date=period_start,
        end_date_exclusive=period_end_exclusive,
    )

    total_spent = sum(amount for _, amount in category_totals)
    top_categories = category_totals[:3]
    summaries: List[TransactionCategorySummary] = []

    for category, amount in top_categories:
        percentage = (amount / total_spent * 100) if total_spent else 0.0
        summaries.append(
            TransactionCategorySummary(
                category=category,
                amount=amount,
                percentage=percentage,
            )
        )

    other_amount = max(total_spent - sum(amount for _, amount in top_categories), 0.0)
    other_percentage = (other_amount / total_spent * 100) if total_spent else 0.0
    summaries.append(
        TransactionCategorySummary(
            category="other",
            amount=other_amount,
            percentage=other_percentage,
        )
    )

    return TransactionSummaryResponse(
        period_start=period_start,
        period_end=period_end,
        total_spent=total_spent,
        categories=summaries,
    )
