CREATE TABLE IF NOT EXISTS accounts (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id            UUID NOT NULL,
  plaid_item_id      UUID NOT NULL,
  plaid_account_id   VARCHAR NOT NULL UNIQUE,
  name               VARCHAR,
  official_name      VARCHAR,
  mask               VARCHAR(8),
  type               VARCHAR,
  subtype            VARCHAR,
  currency           CHAR(3) DEFAULT 'USD',
  current_balance    DECIMAL(18,2),
  available_balance  DECIMAL(18,2),
  created_at         TIMESTAMP DEFAULT now(),
  updated_at         TIMESTAMP DEFAULT now(),
  deleted_at TIMESTAMP DEFAULT NULL
);

-- Backfill columns if table existed from a previous failed migration
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS plaid_item_id UUID;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS plaid_account_id VARCHAR;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'accounts_plaid_account_id_key') THEN
    ALTER TABLE accounts ADD CONSTRAINT accounts_plaid_account_id_key UNIQUE (plaid_account_id);
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS transactions (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id              UUID NOT NULL,
  external_txn_id         VARCHAR UNIQUE,
  amount                  DECIMAL(18,2) NOT NULL CHECK (amount >= 0),
  currency                CHAR(3) DEFAULT 'USD',
  type                    VARCHAR NOT NULL,
  merchant_name           VARCHAR,
  description             TEXT,
  category                VARCHAR,
  authorized_date         DATE,
  posted_date             DATE,
  pending                 BOOLEAN DEFAULT FALSE,
  original_payer_user_id  UUID,
  created_at              TIMESTAMP DEFAULT now(),
  updated_at              TIMESTAMP DEFAULT now(),
  deleted_at TIMESTAMP DEFAULT NULL
);

-- Backfill transactions columns if table existed without them
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS original_payer_user_id UUID;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS posted_date DATE;
