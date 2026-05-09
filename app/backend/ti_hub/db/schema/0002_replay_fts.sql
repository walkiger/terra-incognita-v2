-- Hub replay FTS (M1.2). Source: app/docs/greenfield/implementation/mvp/M1-data-foundation.md § M1.2

CREATE VIRTUAL TABLE replay_events_fts USING fts5 (
  payload_text,
  kind,
  content='',
  tokenize='unicode61 remove_diacritics 2'
);

-- Single-row control for append-driven debounced rebuild signalling.
CREATE TABLE replay_fts_rebuild_signals (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  append_count_since_rebuild INTEGER NOT NULL DEFAULT 0,
  last_append_unix INTEGER NOT NULL DEFAULT 0
);

INSERT INTO replay_fts_rebuild_signals (id, append_count_since_rebuild, last_append_unix)
VALUES (1, 0, 0);

CREATE TRIGGER replay_events_ai_fts_signals
AFTER INSERT ON replay_events
BEGIN
  INSERT INTO replay_events_fts(rowid, payload_text, kind)
  VALUES (NEW.id, NEW.payload_json, NEW.kind);
  UPDATE replay_fts_rebuild_signals
  SET
    append_count_since_rebuild = append_count_since_rebuild + 1,
    last_append_unix = CAST(strftime('%s','now') AS INTEGER)
  WHERE id = 1;
END;

CREATE TRIGGER replay_events_au_fts_signals
AFTER UPDATE OF payload_json, kind ON replay_events
BEGIN
  INSERT INTO replay_events_fts(replay_events_fts, rowid, payload_text, kind)
    VALUES ('delete', OLD.id, OLD.payload_json, OLD.kind);
  INSERT INTO replay_events_fts(rowid, payload_text, kind)
    VALUES (NEW.id, NEW.payload_json, NEW.kind);
  UPDATE replay_fts_rebuild_signals
  SET
    append_count_since_rebuild = append_count_since_rebuild + 1,
    last_append_unix = CAST(strftime('%s','now') AS INTEGER)
  WHERE id = 1;
END;

CREATE TRIGGER replay_events_ad_fts_signals
AFTER DELETE ON replay_events
BEGIN
  INSERT INTO replay_events_fts(replay_events_fts, rowid, payload_text, kind)
    VALUES ('delete', OLD.id, OLD.payload_json, OLD.kind);
  UPDATE replay_fts_rebuild_signals
  SET
    append_count_since_rebuild = append_count_since_rebuild + 1,
    last_append_unix = CAST(strftime('%s','now') AS INTEGER)
  WHERE id = 1;
END;
