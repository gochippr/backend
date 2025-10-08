import logging
from datetime import datetime
from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel

from database.supabase.orm import get_connection
from utils.database import row_to_model_with_cursor

logger = logging.getLogger(__name__)

FriendshipStatus = Literal["pending", "accepted", "blocked"]


class Friendship(BaseModel):
    user_id: str
    friend_user_id: str
    initiator_user_id: str
    status: str  # pending|accepted|blocked (enforced in code)
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]


def _normalize_pair(a: str, b: str) -> Tuple[str, str]:
    # Ensure deterministic ordering to match PK (user_id, friend_user_id)
    return (a, b) if str(a) < str(b) else (b, a)


def get_friendship(
    user_id: str,
    friend_user_id: str,
    *,
    include_deleted: bool = False,
) -> Optional[Friendship]:
    a, b = _normalize_pair(user_id, friend_user_id)
    conn = get_connection()
    cur = conn.cursor()
    try:
        sql = "SELECT * FROM friendships WHERE user_id = %(a)s::uuid AND friend_user_id = %(b)s::uuid"
        if not include_deleted:
            sql += " AND deleted_at IS NULL"
        cur.execute(sql, {"a": a, "b": b})
        row = cur.fetchone()
        return row_to_model_with_cursor(row, Friendship, cur) if row else None
    finally:
        cur.close()
        conn.close()


def list_friends_for_user(
    user_id: str,
    only_accepted: bool = True,
) -> List[Friendship]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        if only_accepted:
            cur.execute(
                """
                SELECT * FROM friendships
                WHERE (user_id = %(uid)s::uuid OR friend_user_id = %(uid)s::uuid)
                  AND status = 'accepted'
                  AND deleted_at IS NULL
                ORDER BY created_at DESC
                """,
                {"uid": user_id},
            )
        else:
            cur.execute(
                """
                SELECT * FROM friendships
                WHERE (user_id = %(uid)s::uuid OR friend_user_id = %(uid)s::uuid)
                  AND deleted_at IS NULL
                ORDER BY created_at DESC
                """,
                {"uid": user_id},
            )
        rows = cur.fetchall()
        return [row_to_model_with_cursor(r, Friendship, cur) for r in rows]
    finally:
        cur.close()
        conn.close()


def list_friendships_by_status(user_id: str, status: FriendshipStatus) -> List[Friendship]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT * FROM friendships
            WHERE (user_id = %(uid)s::uuid OR friend_user_id = %(uid)s::uuid)
              AND status = %(status)s
              AND deleted_at IS NULL
            ORDER BY created_at DESC
            """,
            {"uid": user_id, "status": status},
        )
        rows = cur.fetchall()
        return [row_to_model_with_cursor(r, Friendship, cur) for r in rows]
    finally:
        cur.close()
        conn.close()


def create_friendship(
    user_id: str,
    friend_user_id: str,
    *,
    initiator_user_id: str,
    status: FriendshipStatus = "pending",
) -> Friendship:
    a, b = _normalize_pair(user_id, friend_user_id)
    conn = get_connection()
    cur = conn.cursor()
    try:
        sql = """
            INSERT INTO friendships (user_id, friend_user_id, initiator_user_id, status, created_at, updated_at, deleted_at)
            VALUES (%(a)s::uuid, %(b)s::uuid, %(initiator)s::uuid, %(status)s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL)
            ON CONFLICT (user_id, friend_user_id) DO UPDATE SET
              status = EXCLUDED.status,
              updated_at = CURRENT_TIMESTAMP,
              deleted_at = NULL,
              initiator_user_id = CASE
                WHEN friendships.status != 'pending' THEN EXCLUDED.initiator_user_id
                ELSE friendships.initiator_user_id
              END
            RETURNING *
        """
        cur.execute(
            sql,
            {
                "a": a,
                "b": b,
                "status": status,
                "initiator": initiator_user_id,
            },
        )
        row = cur.fetchone()
        conn.commit()
        return row_to_model_with_cursor(row, Friendship, cur)
    except Exception as e:
        conn.rollback()
        logger.error(
            f"Error creating/updating friendship ({user_id},{friend_user_id}): {e}"
        )
        raise
    finally:
        cur.close()
        conn.close()


def update_friendship_status(
    user_id: str,
    friend_user_id: str,
    status: FriendshipStatus,
) -> Friendship:
    a, b = _normalize_pair(user_id, friend_user_id)
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE friendships
            SET status = %(status)s,
                updated_at = CURRENT_TIMESTAMP,
                deleted_at = NULL
            WHERE user_id = %(a)s::uuid AND friend_user_id = %(b)s::uuid
              AND deleted_at IS NULL
            RETURNING *
            """,
            {"status": status, "a": a, "b": b},
        )
        row = cur.fetchone()
        if not row:
            raise Exception("Friendship not found")
        conn.commit()
        return row_to_model_with_cursor(row, Friendship, cur)
    except Exception as e:
        conn.rollback()
        logger.error(
            f"Error updating friendship status ({user_id},{friend_user_id}) -> {status}: {e}"
        )
        raise
    finally:
        cur.close()
        conn.close()


def delete_friendship(user_id: str, friend_user_id: str) -> None:
    a, b = _normalize_pair(user_id, friend_user_id)
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE friendships
            SET deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %(a)s::uuid AND friend_user_id = %(b)s::uuid
              AND deleted_at IS NULL
            """,
            {"a": a, "b": b},
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error deleting friendship ({user_id},{friend_user_id}): {e}")
        raise
    finally:
        cur.close()
        conn.close()
