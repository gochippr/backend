from datetime import datetime
from decimal import Decimal
from typing import List, Optional
 

from pydantic import BaseModel


class AccountResponse(BaseModel):
    id: str
    user_id: str
    name: str
    type: str  # 'personal' or 'debt_ledger'
    description: Optional[str]
    external_account_id: Optional[str]
    external_institution_id: Optional[str]
    mask: Optional[str]
    official_name: Optional[str]
    subtype: Optional[str]
    verification_status: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AccountBalanceResponse(BaseModel):
    account_id: str
    account_name: str
    account_type: str
    current_balance: Decimal
    available_balance: Optional[Decimal]
    currency: str = "USD"


class UserAccountsResponse(BaseModel):
    accounts: List[AccountResponse]


class UserBalanceResponse(BaseModel):
    total_balance: float
    friend_credit: float
    friend_debt: float
    real_credit_available: float
