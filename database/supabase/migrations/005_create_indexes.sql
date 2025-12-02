DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'friendships_user_id_fkey') THEN
    ALTER TABLE friendships
      ADD CONSTRAINT friendships_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'friendships_friend_user_id_fkey') THEN
    ALTER TABLE friendships
      ADD CONSTRAINT friendships_friend_user_id_fkey
      FOREIGN KEY (friend_user_id) REFERENCES users(id) ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'plaid_items_user_id_fkey') THEN
    ALTER TABLE plaid_items
      ADD CONSTRAINT plaid_items_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'accounts_user_id_fkey') THEN
    ALTER TABLE accounts
      ADD CONSTRAINT accounts_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'accounts_plaid_item_id_fkey') THEN
    ALTER TABLE accounts
      ADD CONSTRAINT accounts_plaid_item_id_fkey
      FOREIGN KEY (plaid_item_id) REFERENCES plaid_items(id) ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'transactions_account_id_fkey') THEN
    ALTER TABLE transactions
      ADD CONSTRAINT transactions_account_id_fkey
      FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'transactions_original_payer_user_id_fkey') THEN
    ALTER TABLE transactions
      ADD CONSTRAINT transactions_original_payer_user_id_fkey
      FOREIGN KEY (original_payer_user_id) REFERENCES users(id) ON DELETE SET NULL;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'transaction_splits_transaction_id_fkey') THEN
    ALTER TABLE transaction_splits
      ADD CONSTRAINT transaction_splits_transaction_id_fkey
      FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'transaction_splits_debtor_user_id_fkey') THEN
    ALTER TABLE transaction_splits
      ADD CONSTRAINT transaction_splits_debtor_user_id_fkey
      FOREIGN KEY (debtor_user_id) REFERENCES users(id) ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'settlements_from_user_id_fkey') THEN
    ALTER TABLE settlements
      ADD CONSTRAINT settlements_from_user_id_fkey
      FOREIGN KEY (from_user_id) REFERENCES users(id) ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'settlements_to_user_id_fkey') THEN
    ALTER TABLE settlements
      ADD CONSTRAINT settlements_to_user_id_fkey
      FOREIGN KEY (to_user_id) REFERENCES users(id) ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'settlements_related_txn_id_fkey') THEN
    ALTER TABLE settlements
      ADD CONSTRAINT settlements_related_txn_id_fkey
      FOREIGN KEY (related_txn_id) REFERENCES transactions(id) ON DELETE SET NULL;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at);

CREATE INDEX IF NOT EXISTS idx_friendships_friend_user_id ON friendships (friend_user_id);

CREATE INDEX IF NOT EXISTS idx_plaid_items_user_id ON plaid_items (user_id);

CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts (user_id);
CREATE INDEX IF NOT EXISTS idx_accounts_plaid_item_id ON accounts (plaid_item_id);

CREATE INDEX IF NOT EXISTS idx_transactions_account_id_posted_date ON transactions (account_id, posted_date);
CREATE INDEX IF NOT EXISTS idx_transactions_original_payer_user_id ON transactions (original_payer_user_id);

CREATE INDEX IF NOT EXISTS idx_transaction_splits_debtor_user_id ON transaction_splits (debtor_user_id);
CREATE INDEX IF NOT EXISTS idx_transaction_splits_transaction_id ON transaction_splits (transaction_id);

CREATE INDEX IF NOT EXISTS idx_settlements_from_to ON settlements (from_user_id, to_user_id);
CREATE INDEX IF NOT EXISTS idx_settlements_created_at ON settlements (created_at);
