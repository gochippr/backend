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

-- Add foreign key constraint to existing user_plaid_items table
ALTER TABLE user_plaid_items 
ADD CONSTRAINT fk_user_plaid_items_user_id 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Create index on email for faster lookups
CREATE INDEX idx_users_email ON users(email);

-- Create index on provider for filtering by auth provider
CREATE INDEX idx_users_provider ON users(provider);