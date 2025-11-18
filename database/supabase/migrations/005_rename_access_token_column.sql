-- Rename access_token column to access_token_encrypted
ALTER TABLE user_plaid_items 
RENAME COLUMN access_token TO access_token_encrypted; 