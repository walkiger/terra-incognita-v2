# Entscheidungen — Übersicht (v2)

**Kanone (Thin-Shell MVP):** [`app/docs/greenfield/decisions/README.md`](../../app/docs/greenfield/decisions/README.md) — dort liegen die ADRs für das neue Produkt.

**Historischer Anhang (Persistenz DuckDB-Ära, archiviert):** [`decisions-archive-persistence-duckdb-era.md`](decisions-archive-persistence-duckdb-era.md) — nur Kontext; technische Kanone für Speicher ist Greenfield **SQLite/Litestream** (siehe ADR‑001 im Ordner oben).

---

**2026-05-09 — Orch:** `.agent-os/pr-spec.json` auf Branch **`chore/knowledge-research-corpus`** zurückgeführt (vorher fälschlich M0.1/`main`). Lokaler Testlauf: `py -m pytest tests/test_repo_layout.py -q` → grün.

**2026-05-09 — Orch:** Ungetracktes **`scripts/`**‑Tooling (CI/Agent‑Helfer, Research‑Utilities) **nicht** in den Knowledge‑Corpus‑PR; eigenständiger Follow‑up (Branch‑Vorschlag in `pr-spec` Tasks). Nur CRLF‑Noise auf `scripts/rewrite_legacy_path_references.py` per `git checkout --` bereinigt.

**2026-05-09 — Orch:** PR **#2** squash‑merged nach **`main`**. Folge‑Branch **`chore/agent-scripts-tooling`** für eingechecktes **`scripts/`**‑Tooling (PR **#3**).

**2026-05-09 — Policy:** Regeln angepasst: **Open‑PR‑First** — vor neuen PRs offene PRs gegenüber **`main`** nach CI‑Grün mergen (außer User will Parallel‑Review). **`meta`/formelles Agent‑OS‑Sign‑off** ist **automatisch ALLOW**, blocking nur bei expliziter User‑Eskalation (`PR-WORKFLOW.mdc`, `GLOBAL-CURSOR-RULES-Agent-OS.mdc`, `SUBAGENT-DELEGATION-FALLBACK.mdc`).

**2026-05-09 — MVP:** Umsetzung **M1.1** gestartet (`feature/sqlite-baseline-schema`): Paket `app/backend/ti_hub/db`, Baseline‑DDL + `HubSQLite`/`open_readonly_connection`, Tests unter `tests/db/`.

**2026-05-09 — M0.2:** **`pyproject.toml`** + **`uv.lock`**, Dev‑Extras (`ruff`, `mypy`, `pytest*`, `coverage`), CI über **`uv sync --frozen --extra dev`**. **`requirements-ci.txt`** / **`pytest.ini`** durch Tooling im **`pyproject.toml`** ersetzt. Stub **`app/engine`** (`terra_engine`) für späteres M3‑Paket.
