CREATE TABLE IF NOT EXISTS transaction_splits (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transaction_id   UUID NOT NULL,
  debtor_user_id   UUID NOT NULL,
  amount           DECIMAL(18,2) NOT NULL CHECK (amount > 0),
  share_weight     NUMERIC(8,4),
  note             TEXT,
  created_at       TIMESTAMP DEFAULT now(),
  updated_at       TIMESTAMP DEFAULT now(),
  deleted_at       TIMESTAMP DEFAULT NULL,
  CONSTRAINT transaction_splits_unique_debtor_per_txn UNIQUE (transaction_id, debtor_user_id)
);

CREATE TABLE IF NOT EXISTS settlements (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  from_user_id   UUID NOT NULL,
  to_user_id     UUID NOT NULL,
  amount         DECIMAL(18,2) NOT NULL CHECK (amount > 0),
  currency       CHAR(3) DEFAULT 'USD',
  method         VARCHAR,
  related_txn_id UUID,
  created_at     TIMESTAMP DEFAULT now(),
  updated_at     TIMESTAMP DEFAULT now(),
  deleted_at     TIMESTAMP DEFAULT NULL
);
