"""Repository layer — populated from M1.4 onward.

M1.4: repos.users      — UsersRepository
M1.5: repos.encounters — EncountersRepository
M1.6: repos.replay_events — ReplayEventsRepository
M1.7: repos.snapshots  — SnapshotsRepository

All repositories accept an aiosqlite connection and enforce tenant
isolation via explicit user_id parameters (see BaseRepository in
repos.base, added in M1.4).
"""
