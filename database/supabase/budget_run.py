"""Database access layer for Daily Budget Run feature."""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel

from database.supabase.orm import get_connection
from utils.database import row_to_model_with_cursor

logger = logging.getLogger(__name__)


# ============================================================================
# Models
# ============================================================================


class UserStreak(BaseModel):
    id: str
    user_id: str
    current_streak: int
    longest_streak: int
    streak_start_date: Optional[date]
    last_success_date: Optional[date]
    total_successful_days: int
    created_at: datetime
    updated_at: datetime


class DailyChallenge(BaseModel):
    id: str
    user_id: str
    challenge_date: date
    budget_limit: float
    category_filter: Optional[str]
    challenge_type: str
    description: Optional[str]
    is_completed: bool
    actual_spent: Optional[float]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class UserBadge(BaseModel):
    id: str
    user_id: str
    badge_type: str
    badge_name: str
    badge_description: Optional[str]
    badge_icon: Optional[str]
    earned_at: datetime
    created_at: datetime


class DayStatus(BaseModel):
    day: str  # 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'
    date: str  # ISO date string
    status: str  # 'completed', 'failed', 'pending', 'future'
    spent: Optional[float]
    limit: Optional[float]


class WeeklyProgress(BaseModel):
    id: str
    user_id: str
    week_start_date: date
    day_statuses: List[dict]  # Will be parsed to DayStatus in service layer
    avatar_position: int
    created_at: datetime
    updated_at: datetime


# ============================================================================
# User Streaks
# ============================================================================


def get_user_streak(user_id: str) -> Optional[UserStreak]:
    """Get the streak record for a user."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM user_streaks WHERE user_id = %(user_id)s::uuid",
            {"user_id": user_id},
        )
        row = cur.fetchone()
        return row_to_model_with_cursor(row, UserStreak, cur) if row else None
    finally:
        cur.close()
        conn.close()


def create_user_streak(user_id: str) -> UserStreak:
    """Create a new streak record for a user."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO user_streaks (user_id)
            VALUES (%(user_id)s::uuid)
            ON CONFLICT (user_id) DO NOTHING
            RETURNING *
            """,
            {"user_id": user_id},
        )
        row = cur.fetchone()
        if not row:
            # Already exists, fetch it
            cur.execute(
                "SELECT * FROM user_streaks WHERE user_id = %(user_id)s::uuid",
                {"user_id": user_id},
            )
            row = cur.fetchone()
        conn.commit()
        return row_to_model_with_cursor(row, UserStreak, cur)
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating user streak: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def update_user_streak(
    user_id: str,
    current_streak: int,
    longest_streak: int,
    streak_start_date: Optional[date],
    last_success_date: Optional[date],
    total_successful_days: int,
) -> UserStreak:
    """Update the streak record for a user."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE user_streaks
            SET current_streak = %(current_streak)s,
                longest_streak = %(longest_streak)s,
                streak_start_date = %(streak_start_date)s,
                last_success_date = %(last_success_date)s,
                total_successful_days = %(total_successful_days)s,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %(user_id)s::uuid
            RETURNING *
            """,
            {
                "user_id": user_id,
                "current_streak": current_streak,
                "longest_streak": longest_streak,
                "streak_start_date": streak_start_date,
                "last_success_date": last_success_date,
                "total_successful_days": total_successful_days,
            },
        )
        row = cur.fetchone()
        conn.commit()
        return row_to_model_with_cursor(row, UserStreak, cur)
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating user streak: {e}")
        raise
    finally:
        cur.close()
        conn.close()


# ============================================================================
# Daily Challenges
# ============================================================================


def get_daily_challenge(user_id: str, challenge_date: date) -> Optional[DailyChallenge]:
    """Get a specific daily challenge for a user."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT * FROM daily_challenges
            WHERE user_id = %(user_id)s::uuid AND challenge_date = %(challenge_date)s
            """,
            {"user_id": user_id, "challenge_date": challenge_date},
        )
        row = cur.fetchone()
        return row_to_model_with_cursor(row, DailyChallenge, cur) if row else None
    finally:
        cur.close()
        conn.close()


def create_daily_challenge(
    user_id: str,
    challenge_date: date,
    budget_limit: float,
    category_filter: Optional[str] = None,
    challenge_type: str = "total",
    description: Optional[str] = None,
) -> DailyChallenge:
    """Create a new daily challenge for a user."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO daily_challenges (
                user_id, challenge_date, budget_limit, category_filter, challenge_type, description
            )
            VALUES (
                %(user_id)s::uuid, %(challenge_date)s, %(budget_limit)s,
                %(category_filter)s, %(challenge_type)s, %(description)s
            )
            ON CONFLICT (user_id, challenge_date) DO UPDATE SET
                budget_limit = EXCLUDED.budget_limit,
                category_filter = EXCLUDED.category_filter,
                challenge_type = EXCLUDED.challenge_type,
                description = EXCLUDED.description,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """,
            {
                "user_id": user_id,
                "challenge_date": challenge_date,
                "budget_limit": budget_limit,
                "category_filter": category_filter,
                "challenge_type": challenge_type,
                "description": description,
            },
        )
        row = cur.fetchone()
        conn.commit()
        return row_to_model_with_cursor(row, DailyChallenge, cur)
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating daily challenge: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def complete_daily_challenge(
    user_id: str,
    challenge_date: date,
    actual_spent: float,
    is_completed: bool,
) -> Optional[DailyChallenge]:
    """Mark a daily challenge as complete with actual spending."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE daily_challenges
            SET is_completed = %(is_completed)s,
                actual_spent = %(actual_spent)s,
                completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %(user_id)s::uuid AND challenge_date = %(challenge_date)s
            RETURNING *
            """,
            {
                "user_id": user_id,
                "challenge_date": challenge_date,
                "is_completed": is_completed,
                "actual_spent": actual_spent,
            },
        )
        row = cur.fetchone()
        conn.commit()
        return row_to_model_with_cursor(row, DailyChallenge, cur) if row else None
    except Exception as e:
        conn.rollback()
        logger.error(f"Error completing daily challenge: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def list_challenges_for_week(user_id: str, week_start: date) -> List[DailyChallenge]:
    """Get all daily challenges for a given week."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT * FROM daily_challenges
            WHERE user_id = %(user_id)s::uuid
              AND challenge_date >= %(week_start)s
              AND challenge_date < %(week_start)s + INTERVAL '7 days'
            ORDER BY challenge_date ASC
            """,
            {"user_id": user_id, "week_start": week_start},
        )
        rows = cur.fetchall()
        return [row_to_model_with_cursor(r, DailyChallenge, cur) for r in rows]
    finally:
        cur.close()
        conn.close()


# ============================================================================
# User Badges
# ============================================================================


def get_user_badges(user_id: str) -> List[UserBadge]:
    """Get all badges for a user."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT * FROM user_badges
            WHERE user_id = %(user_id)s::uuid
            ORDER BY earned_at DESC
            """,
            {"user_id": user_id},
        )
        rows = cur.fetchall()
        return [row_to_model_with_cursor(r, UserBadge, cur) for r in rows]
    finally:
        cur.close()
        conn.close()


def award_badge(
    user_id: str,
    badge_type: str,
    badge_name: str,
    badge_description: Optional[str] = None,
    badge_icon: Optional[str] = None,
) -> Optional[UserBadge]:
    """Award a badge to a user (if they don't already have it)."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO user_badges (user_id, badge_type, badge_name, badge_description, badge_icon)
            VALUES (%(user_id)s::uuid, %(badge_type)s, %(badge_name)s, %(badge_description)s, %(badge_icon)s)
            ON CONFLICT (user_id, badge_type) DO NOTHING
            RETURNING *
            """,
            {
                "user_id": user_id,
                "badge_type": badge_type,
                "badge_name": badge_name,
                "badge_description": badge_description,
                "badge_icon": badge_icon,
            },
        )
        row = cur.fetchone()
        conn.commit()
        return row_to_model_with_cursor(row, UserBadge, cur) if row else None
    except Exception as e:
        conn.rollback()
        logger.error(f"Error awarding badge: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def has_badge(user_id: str, badge_type: str) -> bool:
    """Check if a user has a specific badge."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT 1 FROM user_badges
            WHERE user_id = %(user_id)s::uuid AND badge_type = %(badge_type)s
            """,
            {"user_id": user_id, "badge_type": badge_type},
        )
        return cur.fetchone() is not None
    finally:
        cur.close()
        conn.close()


# ============================================================================
# Weekly Progress
# ============================================================================


def get_weekly_progress(user_id: str, week_start: date) -> Optional[WeeklyProgress]:
    """Get the weekly progress for a user."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT * FROM weekly_progress
            WHERE user_id = %(user_id)s::uuid AND week_start_date = %(week_start)s
            """,
            {"user_id": user_id, "week_start": week_start},
        )
        row = cur.fetchone()
        return row_to_model_with_cursor(row, WeeklyProgress, cur) if row else None
    finally:
        cur.close()
        conn.close()


def upsert_weekly_progress(
    user_id: str,
    week_start: date,
    day_statuses: List[dict],
    avatar_position: int,
) -> WeeklyProgress:
    """Create or update weekly progress for a user."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        import json
        cur.execute(
            """
            INSERT INTO weekly_progress (user_id, week_start_date, day_statuses, avatar_position)
            VALUES (%(user_id)s::uuid, %(week_start)s, %(day_statuses)s::jsonb, %(avatar_position)s)
            ON CONFLICT (user_id, week_start_date) DO UPDATE SET
                day_statuses = EXCLUDED.day_statuses,
                avatar_position = EXCLUDED.avatar_position,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """,
            {
                "user_id": user_id,
                "week_start": week_start,
                "day_statuses": json.dumps(day_statuses),
                "avatar_position": avatar_position,
            },
        )
        row = cur.fetchone()
        conn.commit()
        return row_to_model_with_cursor(row, WeeklyProgress, cur)
    except Exception as e:
        conn.rollback()
        logger.error(f"Error upserting weekly progress: {e}")
        raise
    finally:
        cur.close()
        conn.close()


# ============================================================================
# Spending Queries
# ============================================================================


def get_daily_spending(
    user_id: str,
    target_date: date,
    category_filter: Optional[str] = None,
) -> float:
    """Get total spending for a user on a specific date."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        if category_filter:
            cur.execute(
                """
                WITH split_totals AS (
                    SELECT transaction_id, SUM(amount) AS total_amount
                    FROM transaction_splits
                    WHERE deleted_at IS NULL
                    GROUP BY transaction_id
                )
                SELECT COALESCE(SUM(GREATEST(t.amount - COALESCE(st.total_amount, 0), 0)), 0)
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                LEFT JOIN split_totals st ON st.transaction_id = t.id
                WHERE a.user_id = %(user_id)s::uuid
                  AND t.type = 'debit'
                  AND t.pending = FALSE
                  AND t.deleted_at IS NULL
                  AND t.posted_date = %(target_date)s
                  AND LOWER(t.category) = LOWER(%(category)s)
                """,
                {"user_id": user_id, "target_date": target_date, "category": category_filter},
            )
        else:
            cur.execute(
                """
                WITH split_totals AS (
                    SELECT transaction_id, SUM(amount) AS total_amount
                    FROM transaction_splits
                    WHERE deleted_at IS NULL
                    GROUP BY transaction_id
                )
                SELECT COALESCE(SUM(GREATEST(t.amount - COALESCE(st.total_amount, 0), 0)), 0)
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                LEFT JOIN split_totals st ON st.transaction_id = t.id
                WHERE a.user_id = %(user_id)s::uuid
                  AND t.type = 'debit'
                  AND t.pending = FALSE
                  AND t.deleted_at IS NULL
                  AND t.posted_date = %(target_date)s
                """,
                {"user_id": user_id, "target_date": target_date},
            )
        result = cur.fetchone()
        return float(result[0]) if result and result[0] else 0.0
    finally:
        cur.close()
        conn.close()

