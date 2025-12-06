"""
Daily Budget Run API Router

Gamified budgeting endpoints for the streak-based budget challenge feature.
"""

import logging
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from business.budget_run import service as budget_run_service
from database.supabase import budget_run as budget_run_repo
from models.auth_user import AuthUser
from models.budget_run import (BadgeInfo, ChallengeCheckResponse, DayStatus,
                               GameBoard, GameBoardResponse, LeaderboardEntry,
                               LeaderboardResponse, RankInfo, SetBudgetRequest,
                               SetBudgetResponse, StreakInfo, TodayChallenge,
                               UpcomingReward)
from utils.middlewares.auth_user import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/budget-run", tags=["Budget Run"])


# ============================================================================
# Helper Functions
# ============================================================================


def _build_streak_info(streak: budget_run_repo.UserStreak) -> StreakInfo:
    """Convert database streak to response model."""
    return StreakInfo(
        current=streak.current_streak,
        longest=streak.longest_streak,
        start_date=streak.streak_start_date,
        total_successful_days=streak.total_successful_days,
        is_alive=streak.current_streak > 0,
    )


def _build_today_challenge(
    challenge: budget_run_repo.DailyChallenge,
    current_spent: float,
) -> TodayChallenge:
    """Convert database challenge to response model."""
    return TodayChallenge(
        id=challenge.id,
        date=challenge.challenge_date,
        budget_limit=challenge.budget_limit,
        current_spent=current_spent,
        remaining=max(0, challenge.budget_limit - current_spent),
        challenge_type=challenge.challenge_type,
        description=challenge.description,
        is_completed=challenge.is_completed,
        status="success" if current_spent <= challenge.budget_limit else "over_budget",
    )


def _build_badge_info(badge: budget_run_repo.UserBadge) -> BadgeInfo:
    """Convert database badge to response model."""
    return BadgeInfo(
        type=badge.badge_type,
        name=badge.badge_name,
        description=badge.badge_description,
        icon=badge.badge_icon,
        earned_at=badge.earned_at,
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=GameBoardResponse)
async def get_budget_run_status(
    current_user: AuthUser = Depends(get_current_user),
) -> GameBoardResponse:
    """
    Get the complete Daily Budget Run game board status.

    Returns streak info, weekly progress, today's challenge, badges, and more.
    This is the main endpoint for rendering the game UI.
    """
    logger.info(f"Getting budget run status for user {current_user.id}")

    try:
        status = budget_run_service.get_game_board_status(current_user.id)

        # Convert the service response to our response models
        streak = StreakInfo(
            current=status["streak"]["current"],
            longest=status["streak"]["longest"],
            start_date=date.fromisoformat(status["streak"]["startDate"]) if status["streak"]["startDate"] else None,
            total_successful_days=status["streak"]["totalSuccessfulDays"],
            is_alive=status["streak"]["isAlive"],
        )

        days = [
            DayStatus(
                day=d["day"],
                date=date.fromisoformat(d["date"]),
                day_index=d["dayIndex"],
                status=d["status"],
                spent=d["spent"],
                limit=d["limit"],
            )
            for d in status["gameBoard"]["days"]
        ]

        game_board = GameBoard(
            week_start_date=date.fromisoformat(status["gameBoard"]["weekStartDate"]),
            days=days,
            avatar_position=status["gameBoard"]["avatarPosition"],
            days_completed_this_week=status["gameBoard"]["daysCompletedThisWeek"],
        )

        today_challenge = TodayChallenge(
            id=status["todayChallenge"]["id"],
            date=date.fromisoformat(status["todayChallenge"]["date"]),
            budget_limit=status["todayChallenge"]["budgetLimit"],
            current_spent=status["todayChallenge"]["currentSpent"],
            remaining=status["todayChallenge"]["remaining"],
            challenge_type=status["todayChallenge"]["type"],
            description=status["todayChallenge"]["description"],
            is_completed=status["todayChallenge"]["isCompleted"],
            status=status["todayChallenge"]["status"],
        )

        upcoming_reward = UpcomingReward(
            badge=status["upcomingReward"]["badge"],
            name=status["upcomingReward"]["name"],
            icon=status["upcomingReward"]["icon"],
            days_remaining=status["upcomingReward"]["daysRemaining"],
            streak_required=status["upcomingReward"]["streakRequired"],
        )

        badges = [
            BadgeInfo(
                type=b["type"],
                name=b["name"],
                description=b["description"],
                icon=b["icon"],
                earned_at=b["earnedAt"],
            )
            for b in status["badges"]
        ]

        rank = RankInfo(
            name=status["rank"]["name"],
            icon=status["rank"]["icon"],
            level=status["rank"]["level"],
            badge_count=status["rank"]["badgeCount"],
        )

        return GameBoardResponse(
            streak=streak,
            game_board=game_board,
            today_challenge=today_challenge,
            upcoming_reward=upcoming_reward,
            badges=badges,
            rank=rank,
        )
    except Exception as e:
        logger.error(f"Error getting budget run status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get budget run status")


@router.post("/check", response_model=ChallengeCheckResponse)
async def check_daily_challenge(
    current_user: AuthUser = Depends(get_current_user),
) -> ChallengeCheckResponse:
    """
    Check and evaluate today's budget challenge.

    This endpoint:
    1. Calculates actual spending for today
    2. Determines if the user stayed within budget
    3. Updates their streak accordingly
    4. Awards any earned badges

    Call this when the user wants to "submit" their day or after they make a purchase.
    """
    logger.info(f"Checking daily challenge for user {current_user.id}")

    try:
        challenge, is_success, new_badges = budget_run_service.check_and_update_challenge(
            current_user.id
        )

        streak = budget_run_service.get_or_create_streak(current_user.id)

        # Generate fun message
        if is_success:
            if streak.current_streak == 1:
                message = "🎯 First win! Your budget journey begins!"
            elif streak.current_streak == 3:
                message = "🥉 Bronze Saver! You're on fire!"
            elif streak.current_streak == 7:
                message = "🥈 Silver Saver! A whole week! Incredible!"
            elif streak.current_streak >= 14:
                message = f"🏆 {streak.current_streak} days! You're a budget legend!"
            else:
                message = f"✅ Run survived! Streak: {streak.current_streak} days!"
        else:
            message = "💔 Streak broken... but tomorrow is a new day! Start fresh!"

        today_spent = budget_run_repo.get_daily_spending(
            current_user.id,
            date.today(),
            challenge.category_filter,
        )

        return ChallengeCheckResponse(
            success=is_success,
            challenge=_build_today_challenge(challenge, today_spent),
            new_badges=[_build_badge_info(b) for b in new_badges],
            streak_update=_build_streak_info(streak),
            message=message,
        )
    except Exception as e:
        logger.error(f"Error checking daily challenge: {e}")
        raise HTTPException(status_code=500, detail="Failed to check daily challenge")


@router.get("/today", response_model=TodayChallenge)
async def get_today_challenge(
    current_user: AuthUser = Depends(get_current_user),
) -> TodayChallenge:
    """
    Get today's budget challenge details.

    Returns the challenge for today, including budget limit, current spending,
    and whether it's been completed.
    """
    logger.info(f"Getting today's challenge for user {current_user.id}")

    try:
        challenge = budget_run_service.generate_daily_challenge(current_user.id, date.today())
        today_spent = budget_run_repo.get_daily_spending(
            current_user.id,
            date.today(),
            challenge.category_filter,
        )

        return _build_today_challenge(challenge, today_spent)
    except Exception as e:
        logger.error(f"Error getting today's challenge: {e}")
        raise HTTPException(status_code=500, detail="Failed to get today's challenge")


@router.get("/streak", response_model=StreakInfo)
async def get_streak(
    current_user: AuthUser = Depends(get_current_user),
) -> StreakInfo:
    """Get the user's current streak information."""
    logger.info(f"Getting streak for user {current_user.id}")

    try:
        streak = budget_run_service.get_or_create_streak(current_user.id)
        return _build_streak_info(streak)
    except Exception as e:
        logger.error(f"Error getting streak: {e}")
        raise HTTPException(status_code=500, detail="Failed to get streak")


@router.get("/badges", response_model=List[BadgeInfo])
async def get_badges(
    current_user: AuthUser = Depends(get_current_user),
) -> List[BadgeInfo]:
    """Get all badges earned by the user."""
    logger.info(f"Getting badges for user {current_user.id}")

    try:
        badges = budget_run_repo.get_user_badges(current_user.id)
        return [_build_badge_info(b) for b in badges]
    except Exception as e:
        logger.error(f"Error getting badges: {e}")
        raise HTTPException(status_code=500, detail="Failed to get badges")


@router.post("/budget", response_model=SetBudgetResponse)
async def set_daily_budget(
    request: SetBudgetRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> SetBudgetResponse:
    """
    Set a custom budget for today (or a specific date).

    Allows users to customize their daily challenge.
    """
    logger.info(f"Setting custom budget for user {current_user.id}")

    try:
        target_date = request.target_date or date.today()

        challenge = budget_run_service.set_custom_daily_budget(
            user_id=current_user.id,
            target_date=target_date,
            budget_limit=request.budget_limit,
            challenge_type=request.challenge_type,
        )

        today_spent = budget_run_repo.get_daily_spending(
            current_user.id,
            target_date,
            challenge.category_filter,
        )

        return SetBudgetResponse(
            challenge=_build_today_challenge(challenge, today_spent),
            message=f"Challenge set! Stay under ${request.budget_limit:.0f} to keep your streak alive!",
        )
    except Exception as e:
        logger.error(f"Error setting daily budget: {e}")
        raise HTTPException(status_code=500, detail="Failed to set daily budget")


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    current_user: AuthUser = Depends(get_current_user),
) -> LeaderboardResponse:
    """
    Get a simple leaderboard showing top streakers.

    Note: This is a placeholder - in production you'd want to add
    privacy controls and friend-based filtering.
    """
    streak = budget_run_service.get_or_create_streak(current_user.id)
    badges = budget_run_repo.get_user_badges(current_user.id)

    return LeaderboardResponse(
        your_rank=LeaderboardEntry(
            streak=streak.current_streak,
            longest_streak=streak.longest_streak,
            total_successful_days=streak.total_successful_days,
            badge_count=len(badges),
        ),
        message="Full leaderboard coming soon! Keep building your streak!",
    )
