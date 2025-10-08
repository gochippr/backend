import logging
from typing import Dict, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, status

from database.supabase import account as account_repo
from database.supabase import friendship as friendship_repo
from database.supabase import transaction as transaction_repo
from database.supabase import transaction_split as split_repo
from database.supabase import user as user_repo
from database.supabase.balance import get_friend_balances_for_user
from database.supabase.transaction import Transaction
from database.supabase.user import User
from models.auth_user import AuthUser
from models.split import (
    FriendSplitListItem,
    FriendSplitListResponse,
    FriendSplitSummary,
    FriendsSplitSummaryResponse,
    SplitDetailResponse,
    SplitFriend,
    SplitParticipant,
    SplitTotalsResponse,
    SplitTransactionInfo,
    TransactionSplitsResponse,
    TransactionSplitUpsertRequest,
)
from utils.middlewares.auth_user import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/splits", tags=["Splits"])


def _user_to_split_friend(user: User) -> SplitFriend:
    name = (
        user.full_name
        or (" ".join(filter(None, [user.given_name, user.family_name])) or None)
        or user.email.split("@")[0]
    )
    return SplitFriend(
        id=user.id,
        email=user.email,
        name=name,
        photo_url=user.photo_url,
    )


def _get_transaction_payer(transaction: Transaction) -> str:
    if transaction.original_payer_user_id:
        return transaction.original_payer_user_id
    account = account_repo.get_account_by_id(transaction.account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account not found for transaction",
        )
    return account.user_id


def _ensure_can_edit(transaction: Transaction, current_user: AuthUser) -> None:
    payer_user_id = _get_transaction_payer(transaction)
    if payer_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the payer can modify splits",
        )


def _validate_split_inputs(
    *,
    transaction: Transaction,
    payload: TransactionSplitUpsertRequest,
    current_user: AuthUser,
) -> None:
    seen_debtors: Dict[str, bool] = {}
    total = 0.0

    for item in payload.splits:
        if item.debtor_user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot split a transaction with yourself",
            )
        if item.amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Split amounts must be positive",
            )
        if item.debtor_user_id in seen_debtors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate friend in split payload",
            )
        seen_debtors[item.debtor_user_id] = True

        friendship = friendship_repo.get_friendship(
            current_user.id, item.debtor_user_id
        )
        if not friendship or friendship.status != "accepted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can only split with accepted friends",
            )

        total += item.amount

    if total - transaction.amount > 1e-6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Split amounts exceed transaction total",
        )


def _build_participants(
    *,
    transaction: Transaction,
    splits: List[split_repo.TransactionSplit],
    current_user: AuthUser,
) -> Tuple[List[SplitParticipant], float]:
    user_cache: Dict[str, SplitFriend] = {}

    def get_user(user_id: str) -> SplitFriend:
        if user_id not in user_cache:
            user = user_repo.get_user_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Split participant not found",
                )
            user_cache[user_id] = _user_to_split_friend(user)
        return user_cache[user_id]

    total_split = sum(split.amount for split in splits)
    payer_user_id = _get_transaction_payer(transaction)
    payer_share = max(transaction.amount - total_split, 0.0)

    participants: List[SplitParticipant] = []

    # Debtors
    for split in splits:
        friend = get_user(split.debtor_user_id)
        participants.append(
            SplitParticipant(
                user_id=friend.id,
                email=friend.email,
                name=friend.name,
                photo_url=friend.photo_url,
                amount=split.amount,
                role="debtor",
                is_current_user=friend.id == current_user.id,
            )
        )

    # Payer
    payer_friend = get_user(payer_user_id)
    participants.append(
        SplitParticipant(
            user_id=payer_friend.id,
            email=payer_friend.email,
            name=payer_friend.name,
            photo_url=payer_friend.photo_url,
            amount=payer_share,
            role="payer",
            is_current_user=payer_friend.id == current_user.id,
        )
    )

    return participants, total_split


def _build_transaction_split_response(
    *,
    transaction: Transaction,
    current_user: AuthUser,
) -> TransactionSplitsResponse:
    splits = split_repo.list_splits_for_transaction(transaction.id)
    participants, split_total = _build_participants(
        transaction=transaction,
        splits=splits,
        current_user=current_user,
    )

    payer_user_id = _get_transaction_payer(transaction)

    info = SplitTransactionInfo(
        transaction_id=transaction.id,
        transaction_amount=transaction.amount,
        transaction_currency=transaction.currency,
        transaction_description=transaction.description,
        merchant_name=transaction.merchant_name,
        category=transaction.category,
        type=transaction.type,
        posted_date=transaction.posted_date,
        authorized_date=transaction.authorized_date,
        payer_user_id=payer_user_id,
        split_total=split_total,
    )

    return TransactionSplitsResponse(
        transaction=info,
        participants=participants,
        has_splits=len(splits) > 0,
    )


@router.get("/summary", response_model=SplitTotalsResponse)
async def get_split_totals(
    current_user: AuthUser = Depends(get_current_user),
) -> SplitTotalsResponse:
    owed_to_you, you_owe = get_friend_balances_for_user(current_user.id)
    return SplitTotalsResponse(
        total_owed_to_you=owed_to_you,
        total_you_owe=you_owe,
        net_balance=owed_to_you - you_owe,
    )


@router.get("/friends", response_model=FriendsSplitSummaryResponse)
async def list_friend_balances(
    current_user: AuthUser = Depends(get_current_user),
) -> FriendsSplitSummaryResponse:
    balances = split_repo.list_friend_balances_for_user(current_user.id)
    owed_total = 0.0
    owes_total = 0.0
    summaries: List[FriendSplitSummary] = []

    for balance in balances:
        friend_user = user_repo.get_user_by_id(balance.friend_user_id)
        if not friend_user:
            logger.warning(
                "Skipping split summary for missing user %s", balance.friend_user_id
            )
            continue
        friend = _user_to_split_friend(friend_user)
        owed_total += balance.amount_owed_to_user
        owes_total += balance.amount_user_owes
        summaries.append(
            FriendSplitSummary(
                friend=friend,
                amount_owed_to_you=balance.amount_owed_to_user,
                amount_you_owe=balance.amount_user_owes,
                net_balance=balance.amount_owed_to_user - balance.amount_user_owes,
            )
        )

    totals = SplitTotalsResponse(
        total_owed_to_you=owed_total,
        total_you_owe=owes_total,
        net_balance=owed_total - owes_total,
    )
    summaries.sort(key=lambda item: item.net_balance, reverse=True)

    return FriendsSplitSummaryResponse(totals=totals, friends=summaries)


@router.get("/friends/{friend_user_id}", response_model=FriendSplitListResponse)
async def list_splits_for_friend(
    friend_user_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> FriendSplitListResponse:
    friend_user = user_repo.get_user_by_id(friend_user_id)
    if not friend_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Friend not found"
        )

    friendship = friendship_repo.get_friendship(current_user.id, friend_user_id)
    if not friendship or friendship.status != "accepted":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Friendship not accepted"
        )

    friend_model = _user_to_split_friend(friend_user)

    splits = split_repo.list_splits_between_users(current_user.id, friend_user_id)
    items: List[FriendSplitListItem] = []
    you_owe = 0.0
    they_owe = 0.0

    for split in splits:
        if (
            split.payer_user_id == current_user.id
            and split.debtor_user_id == friend_user_id
        ):
            direction = "they_owe"
            share = split.amount
            they_owe += share
        elif (
            split.payer_user_id == friend_user_id
            and split.debtor_user_id == current_user.id
        ):
            direction = "you_owe"
            share = split.amount
            you_owe += share
        else:
            logger.debug(
                "Skipping split %s for user %s friend %s due to unexpected role",
                split.id,
                current_user.id,
                friend_user_id,
            )
            continue

        items.append(
            FriendSplitListItem(
                split_id=split.id,
                transaction_id=split.transaction_id,
                transaction_amount=split.transaction_amount,
                transaction_currency=split.transaction_currency,
                transaction_description=split.transaction_description,
                merchant_name=split.merchant_name,
                category=split.category,
                posted_date=split.posted_date,
                created_at=split.created_at,
                updated_at=split.updated_at,
                share_amount=share,
                direction=direction,
                note=split.note,
                payer_user_id=split.payer_user_id,
            )
        )

    totals = SplitTotalsResponse(
        total_owed_to_you=they_owe,
        total_you_owe=you_owe,
        net_balance=they_owe - you_owe,
    )

    return FriendSplitListResponse(friend=friend_model, totals=totals, splits=items)


@router.get("/{split_id}", response_model=SplitDetailResponse)
async def get_split_detail(
    split_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> SplitDetailResponse:
    split = split_repo.get_split_by_id(split_id)
    if not split:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Split not found"
        )

    if current_user.id not in {split.payer_user_id, split.debtor_user_id}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not part of this split",
        )

    transaction = transaction_repo.get_transaction_by_id(split.transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )

    participants_models, split_total = _build_participants(
        transaction=transaction,
        splits=split_repo.list_splits_for_transaction(transaction.id),
        current_user=current_user,
    )

    direction = "they_owe" if split.payer_user_id == current_user.id else "you_owe"
    can_edit = split.payer_user_id == current_user.id

    info = SplitTransactionInfo(
        transaction_id=transaction.id,
        transaction_amount=transaction.amount,
        transaction_currency=transaction.currency,
        transaction_description=transaction.description,
        merchant_name=transaction.merchant_name,
        category=transaction.category,
        type=transaction.type,
        posted_date=transaction.posted_date,
        authorized_date=transaction.authorized_date,
        payer_user_id=_get_transaction_payer(transaction),
        split_total=split_total,
    )

    return SplitDetailResponse(
        split_id=split.id,
        share_amount=split.amount,
        note=split.note,
        direction=direction,
        can_edit=can_edit,
        transaction=info,
        participants=participants_models,
    )


@router.get(
    "/transactions/{transaction_id}",
    response_model=TransactionSplitsResponse,
)
async def get_transaction_splits(
    transaction_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> TransactionSplitsResponse:
    transaction = transaction_repo.get_transaction_by_id(transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )

    _ensure_can_edit(transaction, current_user)
    return _build_transaction_split_response(
        transaction=transaction, current_user=current_user
    )


@router.post(
    "/transactions/{transaction_id}",
    response_model=TransactionSplitsResponse,
    status_code=status.HTTP_200_OK,
)
async def upsert_transaction_splits(
    transaction_id: str,
    payload: TransactionSplitUpsertRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> TransactionSplitsResponse:
    transaction = transaction_repo.get_transaction_by_id(transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )

    _ensure_can_edit(transaction, current_user)
    _validate_split_inputs(
        transaction=transaction, payload=payload, current_user=current_user
    )

    splits_payload = [
        {
            "debtor_user_id": item.debtor_user_id,
            "amount": item.amount,
            "share_weight": None,
            "note": item.note,
        }
        for item in payload.splits
    ]

    try:
        split_repo.replace_transaction_splits(
            transaction_id=transaction.id,
            splits=splits_payload,
        )
    except Exception:
        logger.exception("Failed to upsert splits for transaction %s", transaction_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update splits",
        )

    return _build_transaction_split_response(
        transaction=transaction, current_user=current_user
    )
