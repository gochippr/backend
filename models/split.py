from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr


class SplitTotalsResponse(BaseModel):
    total_owed_to_you: float
    total_you_owe: float
    net_balance: float


class SplitFriend(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str]
    photo_url: Optional[str]


class FriendSplitSummary(BaseModel):
    friend: SplitFriend
    amount_owed_to_you: float
    amount_you_owe: float
    net_balance: float


class FriendsSplitSummaryResponse(BaseModel):
    totals: SplitTotalsResponse
    friends: List[FriendSplitSummary]


class FriendSplitListItem(BaseModel):
    split_id: str
    transaction_id: str
    transaction_amount: float
    transaction_currency: Optional[str]
    transaction_description: Optional[str]
    merchant_name: Optional[str]
    category: Optional[str]
    posted_date: Optional[date]
    created_at: datetime
    updated_at: datetime
    share_amount: float
    direction: Literal["you_owe", "they_owe"]
    note: Optional[str]
    payer_user_id: str


class FriendSplitListResponse(BaseModel):
    friend: SplitFriend
    totals: SplitTotalsResponse
    splits: List[FriendSplitListItem]


class SplitParticipant(BaseModel):
    user_id: str
    email: EmailStr
    name: Optional[str]
    photo_url: Optional[str]
    amount: float
    role: Literal["payer", "debtor"]
    is_current_user: bool


class SplitTransactionInfo(BaseModel):
    transaction_id: str
    transaction_amount: float
    transaction_currency: Optional[str]
    transaction_description: Optional[str]
    merchant_name: Optional[str]
    category: Optional[str]
    type: str
    posted_date: Optional[date]
    authorized_date: Optional[date]
    payer_user_id: str
    split_total: float


class SplitDetailResponse(BaseModel):
    split_id: str
    share_amount: float
    note: Optional[str]
    direction: Literal["you_owe", "they_owe"]
    can_edit: bool
    transaction: SplitTransactionInfo
    participants: List[SplitParticipant]


class TransactionSplitInput(BaseModel):
    debtor_user_id: str
    amount: float
    note: Optional[str] = None


class TransactionSplitUpsertRequest(BaseModel):
    splits: List[TransactionSplitInput]


class TransactionSplitsResponse(BaseModel):
    transaction: SplitTransactionInfo
    participants: List[SplitParticipant]
    has_splits: bool
