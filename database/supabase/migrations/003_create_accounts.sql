-- Create accounts table
CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(255) NOT NULL,
    description TEXT,
    external_account_id VARCHAR(255), -- Plaid account ID
    external_institution_id VARCHAR(255), -- Plaid institution ID
    mask VARCHAR(10), -- Last 4 digits of account
    official_name TEXT,
    subtype VARCHAR(50), -- Plaid account subtype
    verification_status VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(type);
CREATE INDEX IF NOT EXISTS idx_accounts_external_id ON accounts(external_account_id);
