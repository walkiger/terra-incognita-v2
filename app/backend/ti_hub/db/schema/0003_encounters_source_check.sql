-- M1.5 — enforce encounter.source whitelist (SQL parity with Pydantic EncounterSource).

PRAGMA foreign_keys=OFF;

BEGIN TRANSACTION;

CREATE TABLE encounters_new (
  id             INTEGER PRIMARY KEY,
  user_id        INTEGER NOT NULL REFERENCES users(id),
  ts             INTEGER NOT NULL,
  word           TEXT,
  scale          REAL NOT NULL,
  source         TEXT NOT NULL CHECK (source IN ('user_input', 'ghost', 'walk', 'kg_spontaneous', 'replay')),
  context_json   TEXT NOT NULL
);

INSERT INTO encounters_new (id, user_id, ts, word, scale, source, context_json)
SELECT id, user_id, ts, word, scale, source, context_json FROM encounters;

DROP TABLE encounters;

ALTER TABLE encounters_new RENAME TO encounters;

CREATE INDEX idx_encounters_user_ts ON encounters(user_id, ts DESC);

COMMIT;

PRAGMA foreign_keys=ON;
