import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter

from business.plaid_sync.service import sync_all_items_for_user
from integrations.plaid import plaid_client
from models.auth_user import AuthUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plaid", tags=["Plaid Sync"])


@router.post("/sync")
async def sync_plaid_items(
    # current_user: AuthUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Synchronize all active Plaid items for the authenticated user.

    Returns per-item summary and overall timestamps.
    """
    current_user = AuthUser(
        id="fded32b2-2af0-4fca-9b6f-d3979e44c9f8",
        email="",
        name="Test User",
    )
    started_at = datetime.now(timezone.utc)
    items: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    summaries = await sync_all_items_for_user(
        plaid_client=plaid_client, user_id=current_user.id
    )
    for s in summaries:
        items.append(
            {
                "plaid_item_id": s.plaid_item_id,
                "accounts_upserted": s.accounts_upserted,
                "tx_added": s.tx_added,
                "tx_modified": s.tx_modified,
                "tx_removed": s.tx_removed,
                "has_more": s.has_more,
            }
        )
        if s.error_code or s.error_message:
            errors.append(
                {
                    "plaid_item_id": s.plaid_item_id,
                    "code": s.error_code or "unknown_error",
                    "message": s.error_message or "",
                }
            )

    finished_at = datetime.now(timezone.utc)

    logger.info(
        json.dumps(
            {
                "event": "plaid_sync.completed",
                "user_id": current_user.id,
                "items": items,
                "errors": errors,
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
            }
        )
    )

    return {
        "items": items,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "errors": errors,
    }
