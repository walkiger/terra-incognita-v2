# Hub SQLite schema

- `0001_baseline.sql` — initial Hub tables (`users`, sessions, encounters, replay_events, snapshots, `meta`). FTS5 for `replay_events` lands in M1.2 (`0002_replay_fts.sql`).
- `0003_encounters_source_check.sql` — M1.5 CHECK whitelist on `encounters.source`.
- Version in DB is mirrored in `meta.schema_version` and must stay aligned with these files.
