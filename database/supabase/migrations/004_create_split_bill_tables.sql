-- Migration: Create Split Bill Functionality Tables
-- This migration creates the schema for social bill splitting features
-- Compatible with existing user and plaid integration structure

-- Step 1: Create transactions table to store all financial transactions
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plaid_transaction_id VARCHAR(255) UNIQUE, -- NULL for manual entries
    plaid_item_id VARCHAR(255), -- Reference to user_plaid_items
    
    -- Transaction details
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    merchant_name VARCHAR(255),
    merchant_id VARCHAR(255),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    transaction_date DATE NOT NULL,
    transaction_time TIME,
    
    -- AI categorization
    ai_category VARCHAR(100),
    ai_confidence_score DECIMAL(3, 2), -- 0.00 to 1.00
    user_verified_category BOOLEAN DEFAULT FALSE,
    
    -- Manual entry fields
    is_manual BOOLEAN DEFAULT FALSE,
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_transactions_user_id (user_id),
    INDEX idx_transactions_date (transaction_date),
    INDEX idx_transactions_plaid_id (plaid_transaction_id),
    INDEX idx_transactions_category (category)
);

-- Step 2: Create split groups table for managing group expenses
CREATE TABLE IF NOT EXISTS split_groups (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    created_by_user_id VARCHAR(255) NOT NULL REFERENCES users(id),
    
    -- Split details
    total_amount DECIMAL(10, 2) NOT NULL,
    split_type VARCHAR(20) NOT NULL CHECK (split_type IN ('equal', 'percentage', 'amount', 'shares')),
    description TEXT,
    
    -- AI detection
    ai_detected BOOLEAN DEFAULT FALSE,
    ai_confidence_score DECIMAL(3, 2),
    user_confirmed BOOLEAN DEFAULT FALSE,
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'settled', 'cancelled')),
    settled_at TIMESTAMP,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_split_groups_transaction_id (transaction_id),
    INDEX idx_split_groups_created_by (created_by_user_id),
    INDEX idx_split_groups_status (status)
);

-- Step 3: Create split participants table
CREATE TABLE IF NOT EXISTS split_participants (
    id SERIAL PRIMARY KEY,
    split_group_id INTEGER NOT NULL REFERENCES split_groups(id) ON DELETE CASCADE,
    user_id VARCHAR(255) REFERENCES users(id), -- NULL for non-app users
    
    -- Participant details
    email VARCHAR(255), -- For inviting non-users
    phone VARCHAR(20), -- Alternative contact
    name VARCHAR(255), -- Display name for non-users
    
    -- Split details
    amount_owed DECIMAL(10, 2) NOT NULL,
    percentage DECIMAL(5, 2), -- For percentage splits
    shares INTEGER DEFAULT 1, -- For share-based splits
    
    -- Payment tracking
    amount_paid DECIMAL(10, 2) DEFAULT 0,
    payment_status VARCHAR(20) DEFAULT 'pending' CHECK (payment_status IN ('pending', 'partial', 'paid', 'forgiven')),
    
    -- Notifications
    last_reminder_sent TIMESTAMP,
    reminder_count INTEGER DEFAULT 0,
    
    -- Metadata
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP,
    
    -- Ensure either user_id or email is provided
    CONSTRAINT participant_identifier CHECK (user_id IS NOT NULL OR email IS NOT NULL),
    
    -- Indexes
    INDEX idx_split_participants_group_id (split_group_id),
    INDEX idx_split_participants_user_id (user_id),
    INDEX idx_split_participants_status (payment_status)
);

-- Step 4: Create payments table to track settlement
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    participant_id INTEGER NOT NULL REFERENCES split_participants(id) ON DELETE CASCADE,
    payer_user_id VARCHAR(255) REFERENCES users(id),
    
    -- Payment details
    amount DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(50), -- 'venmo', 'zelle', 'cash', 'in-app', etc.
    external_payment_id VARCHAR(255), -- Reference to external payment system
    
    -- Status
    status VARCHAR(20) DEFAULT 'completed' CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_payments_participant_id (participant_id),
    INDEX idx_payments_payer (payer_user_id)
);

-- Step 5: Create debt summary view for easy balance checking
CREATE OR REPLACE VIEW user_debt_summary AS
SELECT 
    p.user_id,
    SUM(CASE WHEN p.payment_status != 'paid' THEN p.amount_owed - p.amount_paid ELSE 0 END) as total_owed,
    SUM(CASE 
        WHEN sg.created_by_user_id = p.user_id AND p2.payment_status != 'paid' 
        THEN p2.amount_owed - p2.amount_paid 
        ELSE 0 
    END) as total_owed_to_me,
    COUNT(DISTINCT CASE WHEN p.payment_status != 'paid' THEN sg.id END) as active_splits_owing,
    COUNT(DISTINCT CASE 
        WHEN sg.created_by_user_id = p.user_id AND p2.payment_status != 'paid' 
        THEN sg.id 
    END) as active_splits_owed_to_me
FROM split_participants p
LEFT JOIN split_groups sg ON p.split_group_id = sg.id
LEFT JOIN split_participants p2 ON p2.split_group_id = sg.id AND p2.user_id != sg.created_by_user_id
WHERE p.user_id IS NOT NULL
GROUP BY p.user_id;

-- Step 6: Create recurring splits table for regular shared expenses
CREATE TABLE IF NOT EXISTS recurring_splits (
    id SERIAL PRIMARY KEY,
    created_by_user_id VARCHAR(255) NOT NULL REFERENCES users(id),
    
    -- Recurrence details
    name VARCHAR(255) NOT NULL,
    description TEXT,
    amount DECIMAL(10, 2) NOT NULL,
    split_type VARCHAR(20) NOT NULL CHECK (split_type IN ('equal', 'percentage', 'amount', 'shares')),
    
    -- Schedule
    frequency VARCHAR(20) NOT NULL CHECK (frequency IN ('weekly', 'biweekly', 'monthly', 'quarterly', 'yearly')),
    day_of_month INTEGER CHECK (day_of_month BETWEEN 1 AND 31),
    day_of_week INTEGER CHECK (day_of_week BETWEEN 0 AND 6), -- 0 = Sunday
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    next_occurrence DATE NOT NULL,
    last_created_at TIMESTAMP,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_recurring_splits_user_id (created_by_user_id),
    INDEX idx_recurring_splits_active (is_active),
    INDEX idx_recurring_splits_next (next_occurrence)
);

-- Step 7: Create recurring split participants table
CREATE TABLE IF NOT EXISTS recurring_split_participants (
    id SERIAL PRIMARY KEY,
    recurring_split_id INTEGER NOT NULL REFERENCES recurring_splits(id) ON DELETE CASCADE,
    user_id VARCHAR(255) REFERENCES users(id),
    email VARCHAR(255),
    
    -- Split details (same structure as regular splits)
    percentage DECIMAL(5, 2),
    shares INTEGER DEFAULT 1,
    fixed_amount DECIMAL(10, 2),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT recurring_participant_identifier CHECK (user_id IS NOT NULL OR email IS NOT NULL),
    
    -- Indexes
    INDEX idx_recurring_participants_split_id (recurring_split_id),
    INDEX idx_recurring_participants_user_id (user_id)
);

-- Step 8: Enable RLS for all new tables
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE split_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE split_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE recurring_splits ENABLE ROW LEVEL SECURITY;
ALTER TABLE recurring_split_participants ENABLE ROW LEVEL SECURITY;

-- Step 9: Create RLS policies for transactions
CREATE POLICY "Users can view own transactions" 
ON transactions FOR SELECT 
USING (user_id = auth.uid()::text);

CREATE POLICY "Users can insert own transactions" 
ON transactions FOR INSERT 
WITH CHECK (user_id = auth.uid()::text);

CREATE POLICY "Users can update own transactions" 
ON transactions FOR UPDATE 
USING (user_id = auth.uid()::text);

-- Step 10: Create RLS policies for split_groups
CREATE POLICY "Users can view splits they created or participate in" 
ON split_groups FOR SELECT 
USING (
    created_by_user_id = auth.uid()::text 
    OR EXISTS (
        SELECT 1 FROM split_participants 
        WHERE split_group_id = split_groups.id 
        AND user_id = auth.uid()::text
    )
);

CREATE POLICY "Users can create splits" 
ON split_groups FOR INSERT 
WITH CHECK (created_by_user_id = auth.uid()::text);

CREATE POLICY "Users can update splits they created" 
ON split_groups FOR UPDATE 
USING (created_by_user_id = auth.uid()::text);

-- Step 11: Create RLS policies for split_participants
CREATE POLICY "Users can view participants in their splits" 
ON split_participants FOR SELECT 
USING (
    user_id = auth.uid()::text 
    OR EXISTS (
        SELECT 1 FROM split_groups 
        WHERE id = split_participants.split_group_id 
        AND (
            created_by_user_id = auth.uid()::text 
            OR EXISTS (
                SELECT 1 FROM split_participants sp 
                WHERE sp.split_group_id = split_groups.id 
                AND sp.user_id = auth.uid()::text
            )
        )
    )
);

CREATE POLICY "Split creators can manage participants" 
ON split_participants FOR ALL 
USING (
    EXISTS (
        SELECT 1 FROM split_groups 
        WHERE id = split_participants.split_group_id 
        AND created_by_user_id = auth.uid()::text
    )
);

-- Step 12: Create trigger functions for updated_at
CREATE TRIGGER update_transactions_updated_at 
    BEFORE UPDATE ON transactions 
    FOR EACH ROW 
    EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER update_split_groups_updated_at 
    BEFORE UPDATE ON split_groups 
    FOR EACH ROW 
    EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER update_recurring_splits_updated_at 
    BEFORE UPDATE ON recurring_splits 
    FOR EACH ROW 
    EXECUTE FUNCTION public.handle_updated_at();

-- Step 13: Create function to auto-detect potential splits
CREATE OR REPLACE FUNCTION detect_potential_splits()
RETURNS TRIGGER AS $$
DECLARE
    avg_amount DECIMAL(10, 2);
    detection_threshold DECIMAL(3, 2) := 1.5; -- 150% of average
BEGIN
    -- Only process for restaurant/bar categories
    IF NEW.category IN ('Food and Drink', 'Restaurants', 'Bars', 'Entertainment') THEN
        -- Get user's average spending for this category
        SELECT AVG(amount) INTO avg_amount
        FROM transactions
        WHERE user_id = NEW.user_id
        AND category = NEW.category
        AND transaction_date > CURRENT_DATE - INTERVAL '3 months'
        AND id != NEW.id;
        
        -- If transaction is significantly higher than average, flag for split
        IF avg_amount IS NOT NULL AND NEW.amount > (avg_amount * detection_threshold) THEN
            -- Create a pending split group
            INSERT INTO split_groups (
                transaction_id, 
                created_by_user_id, 
                total_amount, 
                split_type, 
                ai_detected, 
                ai_confidence_score,
                status
            ) VALUES (
                NEW.id,
                NEW.user_id,
                NEW.amount,
                'equal',
                TRUE,
                LEAST(1.0, (NEW.amount / avg_amount) / 3), -- Confidence based on deviation
                'pending'
            );
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger for auto-detection
CREATE TRIGGER detect_splits_on_transaction
    AFTER INSERT ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION detect_potential_splits();

-- Step 14: Create helper functions for split calculations
CREATE OR REPLACE FUNCTION calculate_split_amounts(
    p_split_group_id INTEGER
) RETURNS TABLE (
    participant_id INTEGER,
    calculated_amount DECIMAL(10, 2)
) AS $$
DECLARE
    v_split_type VARCHAR(20);
    v_total_amount DECIMAL(10, 2);
    v_participant_count INTEGER;
BEGIN
    -- Get split details
    SELECT split_type, total_amount 
    INTO v_split_type, v_total_amount
    FROM split_groups 
    WHERE id = p_split_group_id;
    
    -- Calculate based on split type
    CASE v_split_type
        WHEN 'equal' THEN
            SELECT COUNT(*) INTO v_participant_count 
            FROM split_participants 
            WHERE split_group_id = p_split_group_id;
            
            RETURN QUERY
            SELECT 
                sp.id,
                ROUND(v_total_amount / v_participant_count, 2)
            FROM split_participants sp
            WHERE sp.split_group_id = p_split_group_id;
            
        WHEN 'percentage' THEN
            RETURN QUERY
            SELECT 
                sp.id,
                ROUND(v_total_amount * (sp.percentage / 100), 2)
            FROM split_participants sp
            WHERE sp.split_group_id = p_split_group_id;
            
        WHEN 'shares' THEN
            RETURN QUERY
            WITH total_shares AS (
                SELECT SUM(shares) as total 
                FROM split_participants 
                WHERE split_group_id = p_split_group_id
            )
            SELECT 
                sp.id,
                ROUND(v_total_amount * (sp.shares::DECIMAL / ts.total), 2)
            FROM split_participants sp, total_shares ts
            WHERE sp.split_group_id = p_split_group_id;
            
        WHEN 'amount' THEN
            -- Amounts are already specified
            RETURN QUERY
            SELECT sp.id, sp.amount_owed
            FROM split_participants sp
            WHERE sp.split_group_id = p_split_group_id;
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- Step 15: Grant necessary permissions
GRANT SELECT ON user_debt_summary TO authenticated;
GRANT ALL ON transactions TO authenticated;
GRANT ALL ON split_groups TO authenticated;
GRANT ALL ON split_participants TO authenticated;
GRANT ALL ON payments TO authenticated;
GRANT ALL ON recurring_splits TO authenticated;
GRANT ALL ON recurring_split_participants TO authenticated;

-- Step 16: Create indexes for performance
CREATE INDEX idx_transactions_merchant ON transactions(merchant_name);
CREATE INDEX idx_split_groups_ai_detected ON split_groups(ai_detected) WHERE ai_detected = TRUE;
CREATE INDEX idx_split_participants_email ON split_participants(email) WHERE email IS NOT NULL;
CREATE INDEX idx_payments_status ON payments(status);

-- Migration complete message
DO $$ 
BEGIN
    RAISE NOTICE 'Split bill schema migration completed successfully';
END $$;