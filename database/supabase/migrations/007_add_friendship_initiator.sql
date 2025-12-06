ALTER TABLE friendships
  ADD COLUMN IF NOT EXISTS initiator_user_id UUID;

UPDATE friendships
SET initiator_user_id = COALESCE(initiator_user_id, user_id)
WHERE initiator_user_id IS NULL;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'friendships' AND column_name = 'initiator_user_id'
  ) THEN
    ALTER TABLE friendships
      ALTER COLUMN initiator_user_id SET NOT NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'friendships_initiator_user_id_fkey'
  ) THEN
    ALTER TABLE friendships
      ADD CONSTRAINT friendships_initiator_user_id_fkey
      FOREIGN KEY (initiator_user_id) REFERENCES users(id) ON DELETE CASCADE;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_friendships_initiator_user_id
  ON friendships (initiator_user_id);
