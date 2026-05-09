-- Hub SQLite baseline (M1.1). Source of truth: app/docs/greenfield/architecture/mvp.md § Hub-SQLite-Schema
-- FTS virtual table for replay_events is deferred to M1.2.

CREATE TABLE meta (
  schema_version INTEGER NOT NULL,
  app_version    TEXT NOT NULL,
  installed_at   INTEGER NOT NULL
);

CREATE TABLE users (
  id             INTEGER PRIMARY KEY,
  email          TEXT NOT NULL UNIQUE,
  pwhash_argon2  TEXT NOT NULL,
  created_at     INTEGER NOT NULL,
  status         TEXT NOT NULL CHECK (status IN ('active','disabled')),
  is_admin       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE sessions (
  id            TEXT PRIMARY KEY,
  user_id       INTEGER NOT NULL REFERENCES users(id),
  created_at    INTEGER NOT NULL,
  expires_at    INTEGER NOT NULL,
  scope         TEXT NOT NULL,
  client_label  TEXT
);

CREATE TABLE engine_connections (
  id             TEXT PRIMARY KEY,
  user_id        INTEGER NOT NULL REFERENCES users(id),
  session_id     TEXT NOT NULL REFERENCES sessions(id),
  protocol_ver   TEXT NOT NULL,
  connected_at   INTEGER NOT NULL,
  last_heartbeat INTEGER NOT NULL,
  status         TEXT NOT NULL CHECK (status IN ('online','idle','closed'))
);

CREATE TABLE encounters (
  id             INTEGER PRIMARY KEY,
  user_id        INTEGER NOT NULL REFERENCES users(id),
  ts             INTEGER NOT NULL,
  word           TEXT,
  scale          REAL NOT NULL,
  source         TEXT NOT NULL,
  context_json   TEXT NOT NULL
);
CREATE INDEX idx_encounters_user_ts ON encounters(user_id, ts DESC);

CREATE TABLE replay_events (
  id             INTEGER PRIMARY KEY,
  user_id        INTEGER NOT NULL REFERENCES users(id),
  ts             INTEGER NOT NULL,
  kind           TEXT NOT NULL,
  payload_json   TEXT NOT NULL,
  schema_ver     INTEGER NOT NULL
);
CREATE INDEX idx_replay_user_ts ON replay_events(user_id, ts);

CREATE TABLE snapshots (
  id             INTEGER PRIMARY KEY,
  user_id        INTEGER NOT NULL REFERENCES users(id),
  ts             INTEGER NOT NULL,
  scope          TEXT NOT NULL,
  size_bytes     INTEGER NOT NULL,
  content_sha256 TEXT NOT NULL UNIQUE,
  r2_key         TEXT NOT NULL UNIQUE,
  status         TEXT NOT NULL CHECK (status IN ('uploading','ready','expired'))
);
