ALTER TABLE votes ADD COLUMN IF NOT EXISTS value INTEGER NOT NULL DEFAULT 1;
ALTER TABLE votes ALTER COLUMN value DROP DEFAULT;
