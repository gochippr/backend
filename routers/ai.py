from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from database.supabase import transaction as transaction_repo
from database.supabase import transaction_split as split_repo
from database.supabase.balance import get_friend_balances_for_user
from integrations.gemini import generate_financial_chat_response
from models.ai import ChatMessage, ChatRequest, ChatResponse
from models.auth_user import AuthUser
from utils.middlewares.auth_user import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])

MAX_HISTORY_MESSAGES = 10
RECENT_TRANSACTIONS_LIMIT = 10
SUMMARY_DAYS = 30


def _trim_history(messages: List[ChatMessage]) -> List[ChatMessage]:
    if len(messages) <= MAX_HISTORY_MESSAGES:
        return messages
    return messages[-MAX_HISTORY_MESSAGES:]


def _build_financial_snapshot(user_id: str) -> dict:
    today = date.today()
    start_date = today - timedelta(days=SUMMARY_DAYS)

    spending_by_category = transaction_repo.get_spending_by_category_for_user(
        user_id,
        start_date=start_date,
        end_date_exclusive=today + timedelta(days=1),
    )

    transactions = transaction_repo.list_transactions_for_user(user_id)[:RECENT_TRANSACTIONS_LIMIT]
    transaction_items = [
        {
            "description": txn.description or txn.merchant_name,
            "amount": txn.user_amount if txn.user_amount is not None else txn.amount,
            "category": txn.category,
            "posted_date": txn.posted_date.isoformat() if txn.posted_date else None,
        }
        for txn in transactions
    ]

    friend_credit, friend_debt = get_friend_balances_for_user(user_id)

    friend_balances = split_repo.list_friend_balances_for_user(user_id)
    friend_items = [
        {
            "friend_user_id": balance.friend_user_id,
            "amount_owed_to_you": balance.amount_owed_to_user,
            "amount_you_owe": balance.amount_user_owes,
        }
        for balance in friend_balances
    ]

    snapshot = {
        "spending_window_days": SUMMARY_DAYS,
        "spending_by_category": spending_by_category,
        "recent_transactions": transaction_items,
        "friend_balances_summary": {
            "total_owed_to_you": friend_credit,
            "total_you_owe": friend_debt,
            "per_friend": friend_items,
        },
    }

    return snapshot


def _build_system_prompt(user_name: str | None, snapshot: dict) -> str:
    snapshot_json = json.dumps(snapshot, ensure_ascii=False)
    name = user_name or "the user"
    return (
        "You are Chippr, a personal finance AI assistant. You know the user's "
        "spending data and must answer questions using the provided JSON context. \n"
        "Always explain reasoning referencing the numbers you have. If information "
        "is missing, be transparent that you are estimating. \n"
        "Be concise, friendly, and focus on actionable insights.\n\n"
        f"User: {name}\n"
        f"Financial snapshot: {snapshot_json}"
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    payload: ChatRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> ChatResponse:
    if not payload.messages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No messages provided")

    trimmed = _trim_history(payload.messages)
    latest = trimmed[-1]
    if latest.role != "user":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Last message must be from user")

    snapshot = _build_financial_snapshot(current_user.id)
    system_prompt = _build_system_prompt(current_user.name, snapshot)

    try:
        messages_payload = [message.dict() for message in trimmed]
        reply = generate_financial_chat_response(
            messages=messages_payload,
            system_prompt=system_prompt,
        )
    except Exception as exc:
        logger.exception("AI chat generation failed for user %s", current_user.id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI response failed") from exc

    return ChatResponse(reply=reply, context_used={"snapshot": snapshot})
