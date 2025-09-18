from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AccountBalance(BaseModel):
    available: Optional[float]
    current: Optional[float]
    limit: Optional[float]
    iso_currency_code: Optional[str]
    unofficial_currency_code: Optional[str]


class Account(BaseModel):
    account_id: str
    balances: AccountBalance
    mask: Optional[str]
    name: str
    official_name: Optional[str]
    type: str
    subtype: Optional[str]
    verification_status: Optional[str]


class TransactionLocation(BaseModel):
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip: Optional[str]
    country: Optional[str]
    lat: Optional[float]
    lon: Optional[float]


class Transaction(BaseModel):
    transaction_id: str
    account_id: str
    amount: float
    date: datetime
    name: str
    merchant_name: Optional[str]
    category: Optional[List[str]]
    category_id: Optional[str]
    pending: bool
    location: Optional[TransactionLocation]


class TransactionsResponse(BaseModel):
    transactions: List[Transaction]
    total_transactions: int
    request_id: str


class SyncResponse(BaseModel):
    added: int
    modified: int
    removed: int
    has_more: bool
    next_cursor: Optional[str]
    request_id: str


class ItemStatusError(BaseModel):
    error_type: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
    display_message: Optional[str]
    request_id: Optional[str]


class ItemStatus(BaseModel):
    last_webhook: Optional[str]
    error: Optional[ItemStatusError]


class ItemStatusResponse(BaseModel):
    item_id: str
    institution_id: Optional[str]
    status: Optional[ItemStatus]


class DisconnectResponse(BaseModel):
    removed: bool
    request_id: str


class Institution(BaseModel):
    id: str
    user_id: str
    item_id: str
    institution_id: Optional[str]
    institution_name: Optional[str]
    created_at: str
    updated_at: str
    delete_at: Optional[str]
    is_active: bool


class CredentialsResponse(BaseModel):
    status: str
    environment: str


class SearchResponse(BaseModel):
    transactions: List[Transaction]
    query: str
    message: str


class RefreshResponse(BaseModel):
    success: bool
    item_id: str
    message: str


class AccountsResponse(BaseModel):
    accounts: List[Account]


class BalancesResponse(BaseModel):
    balances: List[Account]


class InstitutionsResponse(BaseModel):
    institutions: List[Institution]
