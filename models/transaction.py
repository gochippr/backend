from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class TransactionResponse(BaseModel):
    id: str
    account_id: str
    external_txn_id: Optional[str]
    amount: float
    currency: Optional[str]
    type: str
    merchant_name: Optional[str]
    description: Optional[str]
    category: Optional[str]
    authorized_date: Optional[date]
    posted_date: Optional[date]
    pending: bool
    original_payer_user_id: Optional[str]
    created_at: datetime


class UserTransactionsResponse(BaseModel):
    transactions: List[TransactionResponse]


class TransactionCategorySummary(BaseModel):
    category: str
    amount: float
    percentage: float


class TransactionSummaryResponse(BaseModel):
    period_start: date
    period_end: date
    total_spent: float
    categories: List[TransactionCategorySummary]
