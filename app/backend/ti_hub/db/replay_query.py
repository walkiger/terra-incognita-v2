"""Hybrid Planner port for replay_events (M1.6, terra-076..082).

Behavioural parity with the legacy DuckDB ``query_events_timeline_page``
(``replay_timeline_window_v3`` / ``v4``) translated to SQLite FTS5:

* ``chronological`` — filter by id/ts/kind plus optional substring or FTS, order ``id ASC``.
* ``bm25_only`` (hybrid) — FTS5 match required, ``score = -bm25(...)``, tie-break ``id ASC``.
* ``substring_only`` (hybrid) — triple-LIKE on ``payload.message`` / ``msg`` / ``word``,
  ``score`` = field hit count (0..3).
* ``combined`` (hybrid) — union of substring and FTS hits; ``α·bm25/(bm25+1) + β·hits/3``.

Notes vs legacy:

* SQLite FTS5 ``bm25(table)`` returns *negative* numbers (smaller = more relevant).
  We negate so "higher = better" matches the legacy DuckDB convention used in ``terra-080``.
* ``NULL → 0`` for missing BM25 in ``combined`` (rows that hit substring only).
* Tie-break is ``id ASC`` (legacy invariant), implemented in the SQL ORDER BY.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import aiosqlite
from models.replay_event import (
    ReplayEvent,
    ReplayQMatch,
    ReplayRankingMode,
    ReplayRankingPolicy,
    ReplayScoreWeights,
)

REPLAY_LIMIT_MAX = 500
REPLAY_Q_MAX_LEN = 128


class InvalidQueryError(ValueError):
    """Raised when query parameters violate semantic constraints (terra-080)."""


@dataclass(frozen=True)
class ReplayQueryRow:
    """Internal carrier — :class:`ReplayEventsRepository` lifts to ``ReplayItem``."""

    event: ReplayEvent
    score: float | None


@dataclass(frozen=True)
class ReplayQueryPage:
    rows: list[ReplayQueryRow]
    truncated: bool
    next_after_id: int | None
    effective_policy: ReplayRankingPolicy | None


def resolve_effective_ranking_policy(
    q: str | None,
    ranking_mode: ReplayRankingMode,
    q_match: ReplayQMatch | None,
    ranking_policy: ReplayRankingPolicy | None,
) -> ReplayRankingPolicy | None:
    """1:1 port of legacy ``resolve_effective_ranking_policy`` (terra-079).

    Returns ``None`` for chronological mode or no-query searches; otherwise the
    explicit policy when given, else the v3 default that mirrors ``q_match``.
    """

    if not q or ranking_mode != "hybrid":
        return None
    if ranking_policy is not None:
        return ranking_policy
    eff_q_match: ReplayQMatch = q_match or "substring"
    return "bm25_only" if eff_q_match == "fts" else "substring_only"


def replay_like_substring_pattern(q: str) -> str:
    """SQLite ``LIKE ? ESCAPE '\\'`` pattern for case-insensitive substring search.

    Escapes ``\\``, ``%``, ``_`` so user input can't widen the match.
    """

    chunks: list[str] = []
    for ch in q:
        if ch in ("\\", "%", "_"):
            chunks.append("\\" + ch)
        else:
            chunks.append(ch)
    return "%" + "".join(chunks) + "%"


def fts5_query_from_user_text(q: str) -> str:
    """Build an FTS5 MATCH expression that token-ANDs user input safely.

    Splits on whitespace; double-quote-escapes each token; joins with space
    (FTS5 implicit AND). Empty input yields ``'""'`` which never matches.
    """

    tokens = [t for t in q.split() if t]
    if not tokens:
        return '""'
    quoted = ['"' + t.replace('"', '""') + '"' for t in tokens]
    return " ".join(quoted)


_SELECT_BASE = "id, user_id, ts, kind, payload_json, schema_ver"


def _decode_payload(raw: Any, *, row_id: int) -> dict[str, Any]:
    text = "" if raw is None else str(raw)
    try:
        decoded = json.loads(text) if text else {}
    except json.JSONDecodeError as exc:
        msg = f"invalid payload_json for replay_event {row_id}"
        raise InvalidQueryError(msg) from exc
    if not isinstance(decoded, dict):
        msg = f"payload_json must decode to object for replay_event {row_id}"
        raise InvalidQueryError(msg)
    return decoded


def _row_to_event(tup: tuple[Any, ...]) -> ReplayEvent:
    rid = int(tup[0])
    return ReplayEvent(
        id=rid,
        user_id=int(tup[1]),
        ts=int(tup[2]),
        kind=str(tup[3]),
        payload=_decode_payload(tup[4], row_id=rid),
        schema_ver=int(tup[5]),
    )


def _validate_q(q: str | None) -> None:
    if q is not None and len(q) > REPLAY_Q_MAX_LEN:
        msg = f"q exceeds REPLAY_Q_MAX_LEN={REPLAY_Q_MAX_LEN}"
        raise InvalidQueryError(msg)


def _normalize_limit(limit: int) -> int:
    return max(1, min(int(limit), REPLAY_LIMIT_MAX))


def _build_filter_clauses(
    *,
    user_id: int,
    after_id: int | None,
    since_ts: int | None,
    until_ts: int | None,
    kind: str | None,
) -> tuple[list[str], list[Any]]:
    clauses: list[str] = ["user_id = ?"]
    params: list[Any] = [user_id]
    if after_id is not None and after_id >= 0:
        clauses.append("id > ?")
        params.append(int(after_id))
    if since_ts is not None:
        clauses.append("ts >= ?")
        params.append(int(since_ts))
    if until_ts is not None:
        clauses.append("ts <= ?")
        params.append(int(until_ts))
    if kind is not None:
        clauses.append("kind = ?")
        params.append(kind)
    return clauses, params


_JSON_FIELDS: tuple[str, ...] = ("$.message", "$.msg", "$.word")


def _substring_filter_sql() -> str:
    parts = [
        f"COALESCE(json_extract(payload_json, '{path}'), '') LIKE ? ESCAPE '\\'"
        for path in _JSON_FIELDS
    ]
    return "(" + " OR ".join(parts) + ")"


def _substring_hits_sql() -> str:
    parts = [
        f"(CASE WHEN COALESCE(json_extract(payload_json, '{path}'), '') "
        f"LIKE ? ESCAPE '\\' THEN 1 ELSE 0 END)"
        for path in _JSON_FIELDS
    ]
    return "(" + " + ".join(parts) + ")"


async def _execute_chronological(
    conn: aiosqlite.Connection,
    *,
    user_id: int,
    cap: int,
    after_id: int | None,
    since_ts: int | None,
    until_ts: int | None,
    kind: str | None,
    q: str | None,
    q_match: ReplayQMatch | None,
) -> list[tuple[Any, ...]]:
    clauses, params = _build_filter_clauses(
        user_id=user_id,
        after_id=after_id,
        since_ts=since_ts,
        until_ts=until_ts,
        kind=kind,
    )
    if q:
        if (q_match or "substring") == "substring":
            pattern = replay_like_substring_pattern(q)
            clauses.append(_substring_filter_sql())
            params.extend([pattern] * 3)
        else:
            clauses.append(
                "id IN (SELECT rowid FROM replay_events_fts WHERE replay_events_fts MATCH ?)"
            )
            params.append(fts5_query_from_user_text(q))
    sql = (
        f"SELECT {_SELECT_BASE} FROM replay_events "
        f"WHERE {' AND '.join(clauses)} "
        f"ORDER BY id ASC LIMIT ?"
    )
    cur = await conn.execute(sql, (*params, cap + 1))
    return [tuple(r) for r in await cur.fetchall()]


async def _execute_bm25_only(
    conn: aiosqlite.Connection,
    *,
    user_id: int,
    cap: int,
    since_ts: int | None,
    until_ts: int | None,
    kind: str | None,
    q: str,
) -> list[tuple[Any, ...]]:
    clauses, params = _build_filter_clauses(
        user_id=user_id,
        after_id=None,
        since_ts=since_ts,
        until_ts=until_ts,
        kind=kind,
    )
    fts_q = fts5_query_from_user_text(q)
    clauses.append("id IN (SELECT rowid FROM replay_events_fts WHERE replay_events_fts MATCH ?)")
    params.append(fts_q)
    sql = (
        f"SELECT {_SELECT_BASE}, "
        f"-(SELECT bm25(replay_events_fts) FROM replay_events_fts "
        f"WHERE replay_events_fts MATCH ? AND rowid = replay_events.id) "
        f"AS replay_score "
        f"FROM replay_events "
        f"WHERE {' AND '.join(clauses)} "
        f"ORDER BY replay_score DESC, id ASC LIMIT ?"
    )
    cur = await conn.execute(sql, (fts_q, *params, cap + 1))
    return [tuple(r) for r in await cur.fetchall()]


async def _execute_substring_only(
    conn: aiosqlite.Connection,
    *,
    user_id: int,
    cap: int,
    since_ts: int | None,
    until_ts: int | None,
    kind: str | None,
    q: str,
) -> list[tuple[Any, ...]]:
    clauses, params = _build_filter_clauses(
        user_id=user_id,
        after_id=None,
        since_ts=since_ts,
        until_ts=until_ts,
        kind=kind,
    )
    pattern = replay_like_substring_pattern(q)
    clauses.append(_substring_filter_sql())
    where_patterns = [pattern] * 3
    params.extend(where_patterns)
    select_patterns = [pattern] * 3
    sql = (
        f"SELECT {_SELECT_BASE}, "
        f"CAST({_substring_hits_sql()} AS REAL) AS replay_score "
        f"FROM replay_events "
        f"WHERE {' AND '.join(clauses)} "
        f"ORDER BY replay_score DESC, id ASC LIMIT ?"
    )
    cur = await conn.execute(sql, (*select_patterns, *params, cap + 1))
    return [tuple(r) for r in await cur.fetchall()]


def _split_score(rows: list[tuple[Any, ...]]) -> list[ReplayQueryRow]:
    out: list[ReplayQueryRow] = []
    for r in rows:
        ev = _row_to_event(r[:6])
        score = float(r[6]) if len(r) > 6 and r[6] is not None else None
        out.append(ReplayQueryRow(event=ev, score=score))
    return out


def _next_cursor(
    rows: list[tuple[Any, ...]],
    *,
    cap: int,
    hybrid: bool,
) -> tuple[bool, int | None, list[tuple[Any, ...]]]:
    truncated = len(rows) > cap
    page = rows[:cap]
    next_after_id: int | None = None
    if not hybrid and truncated and page:
        last_id = page[-1][0]
        if isinstance(last_id, int):
            next_after_id = last_id
    return truncated, next_after_id, page


async def query_replay_window(
    conn: aiosqlite.Connection,
    *,
    user_id: int,
    limit: int,
    after_id: int | None,
    since_ts: int | None,
    until_ts: int | None,
    kind: str | None,
    q: str | None,
    q_match: ReplayQMatch | None,
    ranking_mode: ReplayRankingMode,
    ranking_policy: ReplayRankingPolicy | None,
    score_weights: ReplayScoreWeights,
) -> ReplayQueryPage:
    """Dispatch to the right policy executor and lift to :class:`ReplayQueryPage`.

    ``score_weights`` is unused here for ``bm25_only`` / ``substring_only`` but is
    preserved for echo. ``combined`` is added in commit 4.
    """

    _validate_q(q)
    cap = _normalize_limit(limit)
    eff_policy = resolve_effective_ranking_policy(q, ranking_mode, q_match, ranking_policy)

    rows: list[tuple[Any, ...]]
    if eff_policy == "bm25_only":
        assert q is not None
        rows = await _execute_bm25_only(
            conn,
            user_id=user_id,
            cap=cap,
            since_ts=since_ts,
            until_ts=until_ts,
            kind=kind,
            q=q,
        )
    elif eff_policy == "substring_only":
        assert q is not None
        rows = await _execute_substring_only(
            conn,
            user_id=user_id,
            cap=cap,
            since_ts=since_ts,
            until_ts=until_ts,
            kind=kind,
            q=q,
        )
    elif eff_policy == "combined":
        # Combined policy lands in commit 4. Score-weight echo is preserved.
        msg = "combined policy is not yet implemented (M1.6 commit 4)"
        raise NotImplementedError(msg)
    else:
        rows = await _execute_chronological(
            conn,
            user_id=user_id,
            cap=cap,
            after_id=after_id,
            since_ts=since_ts,
            until_ts=until_ts,
            kind=kind,
            q=q,
            q_match=q_match,
        )

    hybrid = eff_policy is not None
    truncated, next_after_id, page_rows = _next_cursor(rows, cap=cap, hybrid=hybrid)
    return ReplayQueryPage(
        rows=_split_score(page_rows),
        truncated=truncated,
        next_after_id=next_after_id,
        effective_policy=eff_policy,
    )
