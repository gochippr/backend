from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ItemRow:
    id: str  # UUID (DB PK)
    user_id: str  # UUID
    item_id: str  # Plaid external item_id


@dataclass
class SyncSummary:
    plaid_item_id: str  # Plaid external item_id
    accounts_upserted: int
    tx_added: int
    tx_modified: int
    tx_removed: int
    has_more: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "plaid_item_id": self.plaid_item_id,
            "accounts_upserted": self.accounts_upserted,
            "tx_added": self.tx_added,
            "tx_modified": self.tx_modified,
            "tx_removed": self.tx_removed,
            "has_more": self.has_more,
            **(
                {"error_code": self.error_code, "error_message": self.error_message}
                if self.error_code or self.error_message
                else {}
            ),
        }
