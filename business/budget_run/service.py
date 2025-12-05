"""
Daily Budget Run Service

Gamified budgeting with streaks, challenges, and badges.
Think of it as a daily "survival game" where staying within budget keeps your streak alive.
"""

import logging
from datetime import date, timedelta
from enum import Enum
from typing import List, Optional, Tuple

from database.supabase import budget_run as budget_run_repo

logger = logging.getLogger(__name__)


# ============================================================================
# Badge Definitions
# ============================================================================


class BadgeType(str, Enum):
    # Streak-based badges
    BRONZE_SAVER = "bronze_saver"
    SILVER_SAVER = "silver_saver"
    GOLD_SAVER = "gold_saver"
    PLATINUM_SAVER = "platinum_saver"
    DIAMOND_SAVER = "diamond_saver"

    # Milestone badges
    FIRST_WIN = "first_win"
    WEEK_WARRIOR = "week_warrior"
    MONTH_MASTER = "month_master"

    # Special badges
    COMEBACK_KID = "comeback_kid"
    PERFECT_WEEK = "perfect_week"


BADGE_DEFINITIONS = {
    BadgeType.FIRST_WIN: {
        "name": "First Win",
        "description": "Completed your first daily budget challenge!",
        "icon": "🎯",
        "streak_requirement": 1,
    },
    BadgeType.BRONZE_SAVER: {
        "name": "Bronze Saver",
        "description": "Maintained a 3-day budget streak",
        "icon": "🥉",
        "streak_requirement": 3,
    },
    BadgeType.SILVER_SAVER: {
        "name": "Silver Saver",
        "description": "Maintained a 7-day budget streak",
        "icon": "🥈",
        "streak_requirement": 7,
    },
    BadgeType.GOLD_SAVER: {
        "name": "Gold Saver",
        "description": "Maintained a 14-day budget streak",
        "icon": "🥇",
        "streak_requirement": 14,
    },
    BadgeType.PLATINUM_SAVER: {
        "name": "Platinum Saver",
        "description": "Maintained a 30-day budget streak",
        "icon": "💎",
        "streak_requirement": 30,
    },
    BadgeType.DIAMOND_SAVER: {
        "name": "Diamond Saver",
        "description": "Maintained a 100-day budget streak. Legendary!",
        "icon": "👑",
        "streak_requirement": 100,
    },
    BadgeType.WEEK_WARRIOR: {
        "name": "Week Warrior",
        "description": "Completed 7 total successful budget days",
        "icon": "⚔️",
        "total_days_requirement": 7,
    },
    BadgeType.MONTH_MASTER: {
        "name": "Month Master",
        "description": "Completed 30 total successful budget days",
        "icon": "🏆",
        "total_days_requirement": 30,
    },
    BadgeType.PERFECT_WEEK: {
        "name": "Perfect Week",
        "description": "Stayed within budget every day of a week",
        "icon": "✨",
    },
    BadgeType.COMEBACK_KID: {
        "name": "Comeback Kid",
        "description": "Started a new streak after losing one",
        "icon": "🔥",
    },
}


# ============================================================================
# Challenge Generation
# ============================================================================


def _get_day_of_week_name(d: date) -> str:
    """Get lowercase day name (mon, tue, wed, etc.)."""
    return d.strftime("%a").lower()


def _get_week_start(d: date) -> date:
    """Get the Monday of the week containing the given date."""
    return d - timedelta(days=d.weekday())


def _generate_challenge_description(challenge_type: str, budget_limit: float) -> str:
    """Generate a fun challenge description."""
    descriptions = {
        "total": f"Keep total spending under ${budget_limit:.0f} to keep your streak alive!",
        "food": f"Food challenge: Stay under ${budget_limit:.0f} on food & dining",
        "entertainment": f"Entertainment cap: Keep fun spending under ${budget_limit:.0f}",
        "shopping": f"Shopping limit: Stay under ${budget_limit:.0f} on retail therapy",
        "coffee": f"Coffee challenge: Keep caffeine costs under ${budget_limit:.0f}",
    }
    return descriptions.get(challenge_type, f"Stay under ${budget_limit:.0f} today!")


def generate_daily_challenge(
    user_id: str,
    target_date: date,
    default_budget: float = 50.0,
) -> budget_run_repo.DailyChallenge:
    """
    Generate or retrieve the daily challenge for a user.
    Uses smart defaults based on day of week and user history.
    """
    # Check if challenge already exists
    existing = budget_run_repo.get_daily_challenge(user_id, target_date)
    if existing:
        return existing

    # Generate new challenge with smart defaults
    day_name = _get_day_of_week_name(target_date)

    # Weekend vs weekday budget adjustments
    if day_name in ("sat", "sun"):
        budget_limit = default_budget * 1.2  # 20% more on weekends
        challenge_type = "total"
    elif day_name == "fri":
        budget_limit = default_budget * 1.1  # Slightly more on Fridays
        challenge_type = "total"
    else:
        budget_limit = default_budget
        # Vary challenge types during the week
        type_rotation = ["total", "food", "total", "coffee", "total"]
        challenge_type = type_rotation[target_date.weekday()]

    description = _generate_challenge_description(challenge_type, budget_limit)

    category_filter = None if challenge_type == "total" else challenge_type

    return budget_run_repo.create_daily_challenge(
        user_id=user_id,
        challenge_date=target_date,
        budget_limit=budget_limit,
        category_filter=category_filter,
        challenge_type=challenge_type,
        description=description,
    )


# ============================================================================
# Streak Management
# ============================================================================


def get_or_create_streak(user_id: str) -> budget_run_repo.UserStreak:
    """Get the user's streak, creating one if it doesn't exist."""
    streak = budget_run_repo.get_user_streak(user_id)
    if not streak:
        streak = budget_run_repo.create_user_streak(user_id)
    return streak


def check_and_update_challenge(
    user_id: str,
    target_date: Optional[date] = None,
) -> Tuple[budget_run_repo.DailyChallenge, bool, List[budget_run_repo.UserBadge]]:
    """
    Check if the user completed today's challenge and update their streak.

    Returns:
        - Updated challenge
        - Whether the challenge was completed successfully
        - List of newly earned badges
    """
    if target_date is None:
        target_date = date.today()

    # Get or generate today's challenge
    challenge = generate_daily_challenge(user_id, target_date)

    # Get actual spending for the day
    actual_spent = budget_run_repo.get_daily_spending(
        user_id,
        target_date,
        challenge.category_filter,
    )

    # Determine if challenge was completed
    is_success = actual_spent <= challenge.budget_limit

    # Update challenge completion status
    updated_challenge = budget_run_repo.complete_daily_challenge(
        user_id=user_id,
        challenge_date=target_date,
        actual_spent=actual_spent,
        is_completed=is_success,
    )

    # Update streak
    new_badges = _update_streak_and_badges(user_id, target_date, is_success)

    return updated_challenge or challenge, is_success, new_badges


def _update_streak_and_badges(
    user_id: str,
    target_date: date,
    is_success: bool,
) -> List[budget_run_repo.UserBadge]:
    """Update streak and check for new badge eligibility."""
    streak = get_or_create_streak(user_id)
    new_badges: List[budget_run_repo.UserBadge] = []

    yesterday = target_date - timedelta(days=1)
    had_previous_streak = streak.current_streak > 0

    if is_success:
        # Check if this continues or starts a streak
        if streak.last_success_date == yesterday:
            # Continuing streak
            new_streak = streak.current_streak + 1
            streak_start = streak.streak_start_date
        elif streak.last_success_date == target_date:
            # Already recorded today, no change
            return new_badges
        else:
            # Starting new streak
            new_streak = 1
            streak_start = target_date

            # Check for comeback badge
            if had_previous_streak and not budget_run_repo.has_badge(user_id, BadgeType.COMEBACK_KID):
                badge = budget_run_repo.award_badge(
                    user_id=user_id,
                    badge_type=BadgeType.COMEBACK_KID,
                    badge_name=BADGE_DEFINITIONS[BadgeType.COMEBACK_KID]["name"],
                    badge_description=BADGE_DEFINITIONS[BadgeType.COMEBACK_KID]["description"],
                    badge_icon=BADGE_DEFINITIONS[BadgeType.COMEBACK_KID]["icon"],
                )
                if badge:
                    new_badges.append(badge)

        # Update streak record
        new_longest = max(streak.longest_streak, new_streak)
        new_total = streak.total_successful_days + 1

        budget_run_repo.update_user_streak(
            user_id=user_id,
            current_streak=new_streak,
            longest_streak=new_longest,
            streak_start_date=streak_start,
            last_success_date=target_date,
            total_successful_days=new_total,
        )

        # Check for streak-based badges
        new_badges.extend(_check_streak_badges(user_id, new_streak))

        # Check for total-days badges
        new_badges.extend(_check_total_days_badges(user_id, new_total))

    else:
        # Streak broken - reset current streak but keep history
        if streak.last_success_date and streak.last_success_date < target_date:
            budget_run_repo.update_user_streak(
                user_id=user_id,
                current_streak=0,
                longest_streak=streak.longest_streak,
                streak_start_date=None,
                last_success_date=streak.last_success_date,
                total_successful_days=streak.total_successful_days,
            )

    return new_badges


def _check_streak_badges(user_id: str, current_streak: int) -> List[budget_run_repo.UserBadge]:
    """Check and award streak-based badges."""
    new_badges: List[budget_run_repo.UserBadge] = []

    streak_badges = [
        (BadgeType.FIRST_WIN, 1),
        (BadgeType.BRONZE_SAVER, 3),
        (BadgeType.SILVER_SAVER, 7),
        (BadgeType.GOLD_SAVER, 14),
        (BadgeType.PLATINUM_SAVER, 30),
        (BadgeType.DIAMOND_SAVER, 100),
    ]

    for badge_type, requirement in streak_badges:
        if current_streak >= requirement and not budget_run_repo.has_badge(user_id, badge_type):
            badge_def = BADGE_DEFINITIONS[badge_type]
            badge = budget_run_repo.award_badge(
                user_id=user_id,
                badge_type=badge_type,
                badge_name=badge_def["name"],
                badge_description=badge_def["description"],
                badge_icon=badge_def["icon"],
            )
            if badge:
                new_badges.append(badge)

    return new_badges


def _check_total_days_badges(user_id: str, total_days: int) -> List[budget_run_repo.UserBadge]:
    """Check and award total-days-based badges."""
    new_badges: List[budget_run_repo.UserBadge] = []

    total_badges = [
        (BadgeType.WEEK_WARRIOR, 7),
        (BadgeType.MONTH_MASTER, 30),
    ]

    for badge_type, requirement in total_badges:
        if total_days >= requirement and not budget_run_repo.has_badge(user_id, badge_type):
            badge_def = BADGE_DEFINITIONS[badge_type]
            badge = budget_run_repo.award_badge(
                user_id=user_id,
                badge_type=badge_type,
                badge_name=badge_def["name"],
                badge_description=badge_def["description"],
                badge_icon=badge_def["icon"],
            )
            if badge:
                new_badges.append(badge)

    return new_badges


# ============================================================================
# Weekly Progress / Game Board
# ============================================================================


def get_game_board_status(
    user_id: str,
    reference_date: Optional[date] = None,
) -> dict:
    """
    Get the complete game board status for the Daily Budget Run UI.

    Returns a dictionary with:
    - streak info
    - weekly progress (7 tiles for Mon-Sun)
    - avatar position
    - today's challenge
    - upcoming reward
    - user badges
    """
    if reference_date is None:
        reference_date = date.today()

    week_start = _get_week_start(reference_date)
    streak = get_or_create_streak(user_id)

    # Build day statuses for the week
    day_statuses = []
    avatar_position = 0
    days_completed = 0

    for i in range(7):
        day_date = week_start + timedelta(days=i)
        day_name = _get_day_of_week_name(day_date)

        challenge = budget_run_repo.get_daily_challenge(user_id, day_date)

        if day_date > reference_date:
            # Future day
            status = "future"
            spent = None
            limit = None
        elif day_date == reference_date:
            # Today
            if challenge and challenge.completed_at:
                status = "completed" if challenge.is_completed else "failed"
                spent = challenge.actual_spent
                limit = challenge.budget_limit
                if challenge.is_completed:
                    days_completed += 1
                    avatar_position = i + 1
            else:
                # Today's challenge not yet evaluated
                status = "active"
                today_challenge = generate_daily_challenge(user_id, day_date)
                spent = budget_run_repo.get_daily_spending(user_id, day_date, today_challenge.category_filter)
                limit = today_challenge.budget_limit
        else:
            # Past day
            if challenge:
                status = "completed" if challenge.is_completed else "failed"
                spent = challenge.actual_spent
                limit = challenge.budget_limit
                if challenge.is_completed:
                    days_completed += 1
                    avatar_position = i + 1
            else:
                status = "missed"
                spent = None
                limit = None

        day_statuses.append({
            "day": day_name,
            "date": day_date.isoformat(),
            "dayIndex": i,
            "status": status,
            "spent": spent,
            "limit": limit,
        })

    # Get today's challenge details
    today_challenge = generate_daily_challenge(user_id, reference_date)
    today_spent = budget_run_repo.get_daily_spending(
        user_id,
        reference_date,
        today_challenge.category_filter,
    )

    # Calculate upcoming reward
    upcoming_reward = _get_upcoming_reward(streak.current_streak)

    # Get user badges
    badges = budget_run_repo.get_user_badges(user_id)

    # Save weekly progress
    budget_run_repo.upsert_weekly_progress(
        user_id=user_id,
        week_start=week_start,
        day_statuses=day_statuses,
        avatar_position=avatar_position,
    )

    return {
        "streak": {
            "current": streak.current_streak,
            "longest": streak.longest_streak,
            "startDate": streak.streak_start_date.isoformat() if streak.streak_start_date else None,
            "totalSuccessfulDays": streak.total_successful_days,
            "isAlive": streak.current_streak > 0,
        },
        "gameBoard": {
            "weekStartDate": week_start.isoformat(),
            "days": day_statuses,
            "avatarPosition": avatar_position,
            "daysCompletedThisWeek": days_completed,
        },
        "todayChallenge": {
            "id": today_challenge.id,
            "date": today_challenge.challenge_date.isoformat(),
            "budgetLimit": today_challenge.budget_limit,
            "currentSpent": today_spent,
            "remaining": max(0, today_challenge.budget_limit - today_spent),
            "type": today_challenge.challenge_type,
            "description": today_challenge.description,
            "isCompleted": today_challenge.is_completed,
            "status": "success" if today_spent <= today_challenge.budget_limit else "over_budget",
        },
        "upcomingReward": upcoming_reward,
        "badges": [
            {
                "type": b.badge_type,
                "name": b.badge_name,
                "description": b.badge_description,
                "icon": b.badge_icon,
                "earnedAt": b.earned_at.isoformat(),
            }
            for b in badges
        ],
        "rank": _calculate_rank(streak.current_streak, len(badges)),
    }


def _get_upcoming_reward(current_streak: int) -> dict:
    """Get the next badge the user can earn."""
    streak_thresholds = [
        (1, BadgeType.FIRST_WIN),
        (3, BadgeType.BRONZE_SAVER),
        (7, BadgeType.SILVER_SAVER),
        (14, BadgeType.GOLD_SAVER),
        (30, BadgeType.PLATINUM_SAVER),
        (100, BadgeType.DIAMOND_SAVER),
    ]

    for threshold, badge_type in streak_thresholds:
        if current_streak < threshold:
            badge_def = BADGE_DEFINITIONS[badge_type]
            return {
                "badge": badge_type,
                "name": badge_def["name"],
                "icon": badge_def["icon"],
                "daysRemaining": threshold - current_streak,
                "streakRequired": threshold,
            }

    # User has all streak badges
    return {
        "badge": None,
        "name": "Legendary Status Achieved",
        "icon": "👑",
        "daysRemaining": 0,
        "streakRequired": 0,
    }


def _calculate_rank(current_streak: int, badge_count: int) -> dict:
    """Calculate the user's current rank based on streak and badges."""
    if current_streak >= 100:
        rank_name = "Diamond"
        rank_icon = "👑"
        rank_level = 6
    elif current_streak >= 30:
        rank_name = "Platinum"
        rank_icon = "💎"
        rank_level = 5
    elif current_streak >= 14:
        rank_name = "Gold"
        rank_icon = "🥇"
        rank_level = 4
    elif current_streak >= 7:
        rank_name = "Silver"
        rank_icon = "🥈"
        rank_level = 3
    elif current_streak >= 3:
        rank_name = "Bronze"
        rank_icon = "🥉"
        rank_level = 2
    elif current_streak >= 1:
        rank_name = "Starter"
        rank_icon = "🎯"
        rank_level = 1
    else:
        rank_name = "Newcomer"
        rank_icon = "🌱"
        rank_level = 0

    return {
        "name": rank_name,
        "icon": rank_icon,
        "level": rank_level,
        "badgeCount": badge_count,
    }


# ============================================================================
# Challenge Customization
# ============================================================================


def set_custom_daily_budget(
    user_id: str,
    target_date: date,
    budget_limit: float,
    challenge_type: str = "total",
) -> budget_run_repo.DailyChallenge:
    """Allow user to set a custom budget challenge for a specific day."""
    category_filter = None if challenge_type == "total" else challenge_type
    description = _generate_challenge_description(challenge_type, budget_limit)

    return budget_run_repo.create_daily_challenge(
        user_id=user_id,
        challenge_date=target_date,
        budget_limit=budget_limit,
        category_filter=category_filter,
        challenge_type=challenge_type,
        description=description,
    )
