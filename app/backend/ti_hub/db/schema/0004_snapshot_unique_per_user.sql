-- 0004: Change snapshots UNIQUE constraints from global to per-user.
--
-- content_sha256 UNIQUE  →  UNIQUE(user_id, content_sha256)
-- r2_key UNIQUE          →  UNIQUE(user_id, r2_key)
--
-- Two users may upload files with identical content or provisional r2_keys;
-- uniqueness is enforced within each tenant, not across tenants.
-- SQLite requires a full table recreation to change constraints.

PRAGMA foreign_keys=OFF;

BEGIN TRANSACTION;

CREATE TABLE snapshots_new (
  id             INTEGER PRIMARY KEY,
  user_id        INTEGER NOT NULL REFERENCES users(id),
  ts             INTEGER NOT NULL,
  scope          TEXT NOT NULL,
  size_bytes     INTEGER NOT NULL,
  content_sha256 TEXT NOT NULL,
  r2_key         TEXT NOT NULL,
  status         TEXT NOT NULL CHECK (status IN ('uploading','ready','expired')),
  UNIQUE(user_id, content_sha256),
  UNIQUE(user_id, r2_key)
);

INSERT INTO snapshots_new
  SELECT id, user_id, ts, scope, size_bytes, content_sha256, r2_key, status
  FROM snapshots;

DROP TABLE snapshots;

ALTER TABLE snapshots_new RENAME TO snapshots;

CREATE INDEX idx_snapshots_user_ts ON snapshots(user_id, ts);

COMMIT;

PRAGMA foreign_keys=ON;
