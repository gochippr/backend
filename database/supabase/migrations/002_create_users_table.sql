CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    picture TEXT,
    given_name VARCHAR(255),
    family_name VARCHAR(255),
    email_verified BOOLEAN DEFAULT FALSE,
    provider VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add foreign key constraint to existing user_plaid_items table (only if it doesn't exist)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_user_plaid_items_user_id' 
        AND table_name = 'user_plaid_items'
    ) THEN
        ALTER TABLE user_plaid_items 
        ADD CONSTRAINT fk_user_plaid_items_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Create index on email for faster lookups (only if it doesn't exist)
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Create index on provider for filtering by auth provider (only if it doesn't exist)
CREATE INDEX IF NOT EXISTS idx_users_provider ON users(provider);