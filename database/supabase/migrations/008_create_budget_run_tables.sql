-- Daily Budget Run: Gamified streak-based budgeting feature
-- Creates tables for tracking user streaks, daily challenges, and badges

-- User streaks: Tracks consecutive days of staying within budget
CREATE TABLE IF NOT EXISTS user_streaks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    current_streak INTEGER NOT NULL DEFAULT 0,
    longest_streak INTEGER NOT NULL DEFAULT 0,
    streak_start_date DATE,
    last_success_date DATE,
    total_successful_days INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    UNIQUE(user_id)
);

-- Daily challenges: Configurable daily budget targets
CREATE TABLE IF NOT EXISTS daily_challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    challenge_date DATE NOT NULL,
    budget_limit DECIMAL(10,2) NOT NULL,
    category_filter VARCHAR(100), -- NULL means all categories, otherwise specific category
    challenge_type VARCHAR(50) NOT NULL DEFAULT 'total', -- 'total', 'food', 'entertainment', etc.
    description TEXT,
    is_completed BOOLEAN DEFAULT FALSE,
    actual_spent DECIMAL(10,2),
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    UNIQUE(user_id, challenge_date)
);

-- User badges: Achievements earned through consistent budgeting
CREATE TABLE IF NOT EXISTS user_badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    badge_type VARCHAR(50) NOT NULL, -- 'bronze_saver', 'silver_saver', 'gold_saver', 'streak_warrior', etc.
    badge_name VARCHAR(100) NOT NULL,
    badge_description TEXT,
    badge_icon VARCHAR(50), -- emoji or icon identifier
    earned_at TIMESTAMP DEFAULT now(),
    created_at TIMESTAMP DEFAULT now(),
    UNIQUE(user_id, badge_type)
);

-- Weekly progress: Track the 7-day game board state
CREATE TABLE IF NOT EXISTS weekly_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    week_start_date DATE NOT NULL, -- Monday of the week
    day_statuses JSONB NOT NULL DEFAULT '[]', -- Array of {day: 'mon'|'tue'|..., status: 'completed'|'failed'|'pending', spent: number, limit: number}
    avatar_position INTEGER NOT NULL DEFAULT 0, -- 0-6 representing Mon-Sun
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    UNIQUE(user_id, week_start_date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_streaks_user_id ON user_streaks(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_challenges_user_date ON daily_challenges(user_id, challenge_date);
CREATE INDEX IF NOT EXISTS idx_daily_challenges_date ON daily_challenges(challenge_date);
CREATE INDEX IF NOT EXISTS idx_user_badges_user_id ON user_badges(user_id);
CREATE INDEX IF NOT EXISTS idx_weekly_progress_user_week ON weekly_progress(user_id, week_start_date);

