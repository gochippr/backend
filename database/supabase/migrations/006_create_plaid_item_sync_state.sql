-- Create per-item sync state table for Plaid cursors and timestamps
CREATE TABLE IF NOT EXISTS plaid_item_sync_state (
  id BIGSERIAL PRIMARY KEY,
  plaid_item_id UUID NOT NULL UNIQUE REFERENCES plaid_items(id) ON DELETE CASCADE,
  transactions_cursor TEXT NULL,
  accounts_last_synced_at TIMESTAMP NULL,
  updated_at TIMESTAMP DEFAULT now()
);

-- Helpful index if UNIQUE not sufficient for lookups (redundant with UNIQUE)
CREATE UNIQUE INDEX IF NOT EXISTS ux_plaid_item_sync_state_plaid_item_id
  ON plaid_item_sync_state (plaid_item_id);

-- Use explicit schema and place LANGUAGE before AS for compatibility
CREATE OR REPLACE FUNCTION public.set_updated_at_timestamp()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- Ensure trigger exists (drop-then-create to avoid conditional DO block)
DROP TRIGGER IF EXISTS trg_plaid_item_sync_state_updated_at ON plaid_item_sync_state;
CREATE TRIGGER trg_plaid_item_sync_state_updated_at
BEFORE UPDATE ON plaid_item_sync_state
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at_timestamp();
