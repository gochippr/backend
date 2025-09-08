-- Use new table name expected by the codebase
CREATE TABLE IF NOT EXISTS plaid_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    access_token TEXT NOT NULL, -- Encrypted
    item_id VARCHAR(255) NOT NULL,
    institution_id VARCHAR(255),
    institution_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP DEFAULT NULL,
    UNIQUE(user_id, item_id)
);
