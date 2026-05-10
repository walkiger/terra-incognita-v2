"""M1.6 — replay_query Hybrid Planner port (terra-076..082)."""

from __future__ import annotations

import pytest
from models import ReplayEventDraft, ReplayScoreWeights, ReplayWindowRequest
from ti_hub.db.connection import HubSQLite
from ti_hub.db.replay_query import InvalidQueryError
from ti_hub.db.repos import ReplayEventsRepository, UsersRepository


async def _seed_user_and_events(
    hub: HubSQLite,
    *,
    email: str = "rq@example.com",
    fixtures: list[dict[str, object]] | None = None,
) -> int:
    fixtures = fixtures or []
    async with hub.write_session() as conn:
        users = UsersRepository(conn)
        user = await users.create(email, "$argon2id$h")
        repo = ReplayEventsRepository(conn)
        for fx in fixtures:
            ts = int(fx["ts"])  # type: ignore[arg-type]
            kind = str(fx.get("kind", "encounter"))
            payload = dict(fx.get("payload", {}))  # type: ignore[arg-type]
            await repo.append(
                user.id,
                ReplayEventDraft(ts=ts, kind=kind, payload=payload),
            )
        await conn.commit()
        return user.id


@pytest.mark.asyncio
async def test_chronological_order_id_ascending() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid = await _seed_user_and_events(
        hub,
        fixtures=[
            {"ts": 30, "payload": {"message": "third"}},
            {"ts": 10, "payload": {"message": "first"}},
            {"ts": 20, "payload": {"message": "second"}},
        ],
    )

    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        resp = await repo.query_window(uid, ReplayWindowRequest(limit=10))

    assert resp.schema_version == "replay_timeline_window_v4"
    ids = [item.event.id for item in resp.items]
    assert ids == sorted(ids), "chronological must order by id ASC"
    # Score is None in chronological mode.
    assert all(item.score is None for item in resp.items)
    assert resp.effective_policy is None
    assert resp.next_after_id is None
    assert resp.truncated is False
    await hub.close()


@pytest.mark.asyncio
async def test_chronological_pagination_after_id() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid = await _seed_user_and_events(
        hub,
        fixtures=[{"ts": i, "payload": {"i": i}} for i in range(1, 8)],
    )

    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        page1 = await repo.query_window(uid, ReplayWindowRequest(limit=3))
        cursor = page1.next_after_id
        assert cursor is not None
        assert page1.truncated is True
        page2 = await repo.query_window(uid, ReplayWindowRequest(limit=3, after_id=cursor))

    assert [i.event.id for i in page1.items] == [1, 2, 3]
    assert [i.event.id for i in page2.items] == [4, 5, 6]
    await hub.close()


@pytest.mark.asyncio
async def test_chronological_substring_filter() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid = await _seed_user_and_events(
        hub,
        fixtures=[
            {"ts": 1, "payload": {"message": "silver moon"}},
            {"ts": 2, "payload": {"msg": "moonless"}},
            {"ts": 3, "payload": {"word": "lunar"}},
            {"ts": 4, "payload": {"message": "no match"}},
        ],
    )

    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        resp = await repo.query_window(uid, ReplayWindowRequest(q="moon"))

    payloads = [i.event.payload for i in resp.items]
    # message "silver moon" and msg "moonless" both contain 'moon'.
    assert {"message": "silver moon"} in payloads
    assert {"msg": "moonless"} in payloads
    assert {"word": "lunar"} not in payloads
    assert {"message": "no match"} not in payloads
    await hub.close()


@pytest.mark.asyncio
async def test_chronological_q_match_fts() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid = await _seed_user_and_events(
        hub,
        fixtures=[
            {"ts": 1, "payload": {"text": "needle in haystack"}},
            {"ts": 2, "payload": {"text": "haystack only"}},
        ],
    )

    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        resp = await repo.query_window(uid, ReplayWindowRequest(q="needle", q_match="fts"))

    assert len(resp.items) == 1
    assert resp.items[0].event.payload == {"text": "needle in haystack"}
    await hub.close()


@pytest.mark.asyncio
async def test_hybrid_bm25_only_orders_by_relevance() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid = await _seed_user_and_events(
        hub,
        fixtures=[
            {"ts": 1, "payload": {"text": "needle"}},
            {"ts": 2, "payload": {"text": "haystack"}},
            {"ts": 3, "payload": {"text": "needle needle"}},
            {"ts": 4, "payload": {"text": "needle in field"}},
        ],
    )

    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        resp = await repo.query_window(
            uid,
            ReplayWindowRequest(
                q="needle",
                ranking_mode="hybrid",
                ranking_policy="bm25_only",
            ),
        )

    assert resp.effective_policy == "bm25_only"
    # All matching rows have positive scores; non-match excluded.
    assert all(it.score is not None and it.score > 0 for it in resp.items)
    payloads = {tuple(sorted(i.event.payload.items())) for i in resp.items}
    assert (("text", "haystack"),) not in payloads
    # Ordering: highest score first; tie-break by id ASC (legacy invariant).
    scores = [it.score for it in resp.items]
    assert scores == sorted(scores, reverse=True)
    await hub.close()


@pytest.mark.asyncio
async def test_hybrid_substring_only_score_is_field_hit_count() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid = await _seed_user_and_events(
        hub,
        fixtures=[
            # 3-field match (score = 3)
            {"ts": 1, "payload": {"message": "moon", "msg": "moon", "word": "moon"}},
            # 2-field match (score = 2)
            {"ts": 2, "payload": {"message": "moon", "msg": "moon"}},
            # 1-field match (score = 1)
            {"ts": 3, "payload": {"word": "moon"}},
            # no match
            {"ts": 4, "payload": {"message": "sun"}},
        ],
    )

    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        resp = await repo.query_window(
            uid,
            ReplayWindowRequest(
                q="moon",
                ranking_mode="hybrid",
                ranking_policy="substring_only",
            ),
        )

    assert resp.effective_policy == "substring_only"
    # The non-match row must be filtered out.
    assert len(resp.items) == 3
    scores = [item.score for item in resp.items]
    assert scores == [3.0, 2.0, 1.0]
    await hub.close()


@pytest.mark.asyncio
async def test_substring_pattern_escapes_wildcards() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid = await _seed_user_and_events(
        hub,
        fixtures=[
            {"ts": 1, "payload": {"message": "needle"}},
            {"ts": 2, "payload": {"message": "100% match"}},
        ],
    )

    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        # If '%' weren't escaped, this would match 'needle' too.
        resp = await repo.query_window(uid, ReplayWindowRequest(q="100%"))

    payloads = [i.event.payload for i in resp.items]
    assert payloads == [{"message": "100% match"}]
    await hub.close()


@pytest.mark.asyncio
async def test_hybrid_default_policy_resolution() -> None:
    """terra-079: hybrid w/o explicit policy → bm25_only when q_match='fts', else substring_only."""

    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid = await _seed_user_and_events(
        hub,
        fixtures=[{"ts": 1, "payload": {"message": "moon"}}],
    )

    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        sub = await repo.query_window(
            uid,
            ReplayWindowRequest(q="moon", ranking_mode="hybrid", q_match="substring"),
        )
        fts = await repo.query_window(
            uid,
            ReplayWindowRequest(q="moon", ranking_mode="hybrid", q_match="fts"),
        )

    assert sub.effective_policy == "substring_only"
    assert fts.effective_policy == "bm25_only"
    await hub.close()


@pytest.mark.asyncio
async def test_filter_echo_score_weights_returned() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid = await _seed_user_and_events(
        hub,
        fixtures=[{"ts": 1, "payload": {"message": "moon"}}],
    )

    weights = ReplayScoreWeights(bm25=0.7, substring=0.3)
    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        resp = await repo.query_window(
            uid,
            ReplayWindowRequest(
                q="moon",
                ranking_mode="hybrid",
                ranking_policy="bm25_only",
                score_weights=weights,
            ),
        )

    assert resp.score_weights == weights
    await hub.close()


@pytest.mark.asyncio
async def test_tenant_isolation_query_window() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid_a = await _seed_user_and_events(
        hub,
        email="iso-a@example.com",
        fixtures=[{"ts": 1, "payload": {"message": "alpha"}}],
    )
    uid_b = await _seed_user_and_events(
        hub,
        email="iso-b@example.com",
        fixtures=[{"ts": 1, "payload": {"message": "beta"}}],
    )

    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        only_a = await repo.query_window(uid_a, ReplayWindowRequest(q="alpha"))
        only_b = await repo.query_window(uid_b, ReplayWindowRequest(q="beta"))
        a_for_beta = await repo.query_window(uid_a, ReplayWindowRequest(q="beta"))

    assert len(only_a.items) == 1
    assert len(only_b.items) == 1
    assert a_for_beta.items == []
    await hub.close()


@pytest.mark.asyncio
async def test_hybrid_combined_score_blends_bm25_and_substring() -> None:
    """terra-080: ``α · bm25/(bm25+1) + β · hits/3``; both contribute when both match."""

    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid = await _seed_user_and_events(
        hub,
        fixtures=[
            # Substring-only match (no FTS hit on 'moon' because token is in JSON
            # whitespace — but actually 'moon' will match FTS too here, so make it
            # substring-only by using a substring that isn't a full token).
            {"ts": 1, "payload": {"message": "moonlit", "msg": "moonlit"}},
            # FTS + substring (token "moon" exact + substring "moon")
            {"ts": 2, "payload": {"message": "moon", "word": "moon"}},
            # Neither.
            {"ts": 3, "payload": {"message": "sun"}},
        ],
    )

    weights = ReplayScoreWeights(bm25=1.0, substring=1.0)
    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        resp = await repo.query_window(
            uid,
            ReplayWindowRequest(
                q="moon",
                ranking_mode="hybrid",
                ranking_policy="combined",
                score_weights=weights,
            ),
        )

    assert resp.effective_policy == "combined"
    payloads = [it.event.payload for it in resp.items]
    assert {"message": "sun"} not in payloads
    assert all(it.score is not None for it in resp.items)
    # Score is monotonically non-increasing.
    scores = [it.score for it in resp.items]
    assert scores == sorted(scores, reverse=True)
    await hub.close()


@pytest.mark.asyncio
async def test_combined_filter_is_union_of_substring_and_fts() -> None:
    """A row matching only substring (no FTS token hit) must still appear in ``combined``."""

    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid = await _seed_user_and_events(
        hub,
        fixtures=[
            # 'moonlit' is one FTS token; substring 'moon' matches it (LIKE %moon%)
            # but FTS query "moon" would NOT match 'moonlit' as a separate token.
            {"ts": 1, "payload": {"message": "moonlit"}},
            # FTS-only: payload field 'text' is FTS-indexed (raw payload_json) but
            # is not in the substring search field set ($.message/$.msg/$.word).
            {"ts": 2, "payload": {"text": "moon"}},
        ],
    )

    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        resp = await repo.query_window(
            uid,
            ReplayWindowRequest(
                q="moon",
                ranking_mode="hybrid",
                ranking_policy="combined",
            ),
        )

    payloads = [it.event.payload for it in resp.items]
    assert {"message": "moonlit"} in payloads, "substring-only match must be kept"
    assert {"text": "moon"} in payloads, "FTS-only match must be kept"
    await hub.close()


@pytest.mark.asyncio
async def test_combined_null_bm25_coalesces_to_zero() -> None:
    """Substring-only match must contribute α·0 to score (no NULL leak)."""

    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid = await _seed_user_and_events(
        hub,
        fixtures=[
            # Substring-only (no FTS token "moon" because field is "moonlit").
            {"ts": 1, "payload": {"message": "moonlit"}},
        ],
    )

    weights = ReplayScoreWeights(bm25=1.0, substring=0.0)
    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        # bm25=1.0, β=0 → only the BM25 contribution counts; for substring-only
        # rows that's 0 (NULL coalesced) → score == 0.0.
        resp = await repo.query_window(
            uid,
            ReplayWindowRequest(
                q="moon",
                ranking_mode="hybrid",
                ranking_policy="combined",
                score_weights=weights,
            ),
        )

    assert len(resp.items) == 1
    assert resp.items[0].score == pytest.approx(0.0)
    await hub.close()


@pytest.mark.asyncio
async def test_combined_invalid_zero_zero_weights_rejected() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid = await _seed_user_and_events(
        hub,
        fixtures=[{"ts": 1, "payload": {"message": "moon"}}],
    )

    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        with pytest.raises(InvalidQueryError):
            await repo.query_window(
                uid,
                ReplayWindowRequest(
                    q="moon",
                    ranking_mode="hybrid",
                    ranking_policy="combined",
                    score_weights=ReplayScoreWeights(bm25=0.0, substring=0.0),
                ),
            )
    await hub.close()


@pytest.mark.asyncio
async def test_combined_tie_break_id_ascending() -> None:
    """When two rows score identically the lower id wins (terra-080 RAM parity)."""

    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    # Two substring-only rows with identical ``hits/3`` (= 1/3) and no FTS hit
    # → identical combined score → tie-break must be id ASC.
    uid = await _seed_user_and_events(
        hub,
        fixtures=[
            {"ts": 1, "payload": {"message": "moonlit"}},
            {"ts": 2, "payload": {"message": "moonlit"}},
            {"ts": 3, "payload": {"message": "moonlit"}},
        ],
    )

    weights = ReplayScoreWeights(bm25=0.0, substring=1.0)
    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        resp = await repo.query_window(
            uid,
            ReplayWindowRequest(
                q="moon",
                ranking_mode="hybrid",
                ranking_policy="combined",
                score_weights=weights,
            ),
        )

    ids = [it.event.id for it in resp.items]
    scores = [it.score for it in resp.items]
    assert scores == [pytest.approx(1.0 / 3.0)] * len(ids)
    assert ids == sorted(ids), "tie-break must be id ASC"
    await hub.close()


@pytest.mark.asyncio
async def test_combined_score_formula_exact_value() -> None:
    """Pin the exact ``α·bm25/(bm25+1) + β·hits/3`` value with α=β=0.5 (terra-080)."""

    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid = await _seed_user_and_events(
        hub,
        fixtures=[
            # 1-field substring match, no FTS hit (payload uses 'message' but
            # value 'moonlit' contains 'moon' as substring only).
            {"ts": 1, "payload": {"message": "moonlit"}},
        ],
    )

    weights = ReplayScoreWeights(bm25=0.5, substring=0.5)
    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        resp = await repo.query_window(
            uid,
            ReplayWindowRequest(
                q="moon",
                ranking_mode="hybrid",
                ranking_policy="combined",
                score_weights=weights,
            ),
        )

    # bm25 contribution = α · 0 = 0 (substring-only row).
    # substring contribution = β · 1/3.
    expected = 0.5 * 0.0 + 0.5 * (1.0 / 3.0)
    assert len(resp.items) == 1
    assert resp.items[0].score == pytest.approx(expected)
    await hub.close()


@pytest.mark.asyncio
async def test_q_max_length_enforced() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid = await _seed_user_and_events(hub, fixtures=[])

    # Pydantic validates at request-construction time (≤ 128 chars) so we
    # validate the inner guard via a direct call to the query module too.
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ReplayWindowRequest(q="a" * 129)

    from ti_hub.db.replay_query import query_replay_window

    async with hub.write_session() as conn:
        with pytest.raises(InvalidQueryError):
            await query_replay_window(
                conn,
                user_id=uid,
                limit=10,
                after_id=None,
                since_ts=None,
                until_ts=None,
                kind=None,
                q="a" * 200,
                q_match=None,
                ranking_mode="chronological",
                ranking_policy=None,
                score_weights=ReplayScoreWeights(),
            )
    await hub.close()
