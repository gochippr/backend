"""Response models for Daily Budget Run feature."""

from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel


class StreakInfo(BaseModel):
    """User's streak information."""

    current: int
    longest: int
    start_date: Optional[date]
    total_successful_days: int
    is_alive: bool


class DayStatus(BaseModel):
    """Status of a single day on the game board."""

    day: str  # 'mon', 'tue', etc.
    date: date
    day_index: int  # 0-6 for Mon-Sun
    status: Literal["completed", "failed", "active", "future", "missed"]
    spent: Optional[float]
    limit: Optional[float]


class GameBoard(BaseModel):
    """The 7-day game board state."""

    week_start_date: date
    days: List[DayStatus]
    avatar_position: int  # 0-7 representing progress through the week
    days_completed_this_week: int


class TodayChallenge(BaseModel):
    """Today's budget challenge details."""

    id: str
    date: date
    budget_limit: float
    current_spent: float
    remaining: float
    challenge_type: str  # 'total', 'food', 'entertainment', etc.
    description: Optional[str]
    is_completed: bool
    status: Literal["success", "over_budget"]


class UpcomingReward(BaseModel):
    """Next badge the user can earn."""

    badge: Optional[str]
    name: str
    icon: str
    days_remaining: int
    streak_required: int


class BadgeInfo(BaseModel):
    """Badge earned by the user."""

    type: str
    name: str
    description: Optional[str]
    icon: Optional[str]
    earned_at: datetime


class RankInfo(BaseModel):
    """User's current rank."""

    name: str  # 'Bronze', 'Silver', 'Gold', etc.
    icon: str
    level: int  # 0-6
    badge_count: int


class GameBoardResponse(BaseModel):
    """Complete game board status for the Daily Budget Run UI."""

    streak: StreakInfo
    game_board: GameBoard
    today_challenge: TodayChallenge
    upcoming_reward: UpcomingReward
    badges: List[BadgeInfo]
    rank: RankInfo


class ChallengeCheckResponse(BaseModel):
    """Response after checking/completing a challenge."""

    success: bool
    challenge: TodayChallenge
    new_badges: List[BadgeInfo]
    streak_update: StreakInfo
    message: str


class SetBudgetRequest(BaseModel):
    """Request to set a custom daily budget."""

    budget_limit: float
    challenge_type: str = "total"
    target_date: Optional[date] = None


class SetBudgetResponse(BaseModel):
    """Response after setting a custom budget."""

    challenge: TodayChallenge
    message: str


class LeaderboardEntry(BaseModel):
    """Single entry in the leaderboard."""

    streak: int
    longest_streak: int
    total_successful_days: int
    badge_count: int


class LeaderboardResponse(BaseModel):
    """Leaderboard response."""

    your_rank: LeaderboardEntry
    message: str

