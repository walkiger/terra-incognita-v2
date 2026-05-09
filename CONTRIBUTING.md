# Contributing

Danke für Beiträge zu **terra-incognita-v2**. Kurzfassung: **Produktcode und spätere Service-Bundles liegen unter [`app/`](app/README.md)**; **Deploy/Infra** unter **`deploy/`** am Repo-Root (Greenfield **M0**).

## Vor jedem Code-Beitrag

Lies die festgelegte Reihenfolge in **[`app/docs/greenfield/README.md`](app/docs/greenfield/README.md)** (Abschnitt „Lesereihenfolge“), mindestens:

1. Diese README und **[`app/docs/greenfield/architecture/mvp.md`](app/docs/greenfield/architecture/mvp.md)**, bevor du am Thin-Shell-MVP arbeitest.
2. Für den aktuellen MVP-Schritt die Datei **`app/docs/greenfield/implementation/mvp/M0..M8-*.md`** bzw. **`00-index.md`** (Status-Tabelle).

Weitere Einstiege: **[`CLAUDE.md`](CLAUDE.md)**, **[`Anweisungen.md`](Anweisungen.md)**.

## Layout (nach M0.1)

| Bereich | Pfad |
|---------|------|
| Produkt + Greenfield-Doku | **`app/`** (`app/docs/greenfield/`, `app/backend`, `app/engine`, `app/web`, …) |
| Preseed-Knowledge (Snapshot) | **`knowledge/`** (`preseed_v2.json`, `verify.py`) |
| Research-Korpus (JSON-Schichten, keine PDFs im Git) | **`research/`** (`extracted/`, `schema/`, siehe `research/README.md`) |
| Compose / Ansible (Bootstrap) | **`deploy/`** |
| Lokale Geheimnisse (nicht committen) | **`secrets/`** (nur Stub `.gitkeep` ist getrackt) |
| Repo-weite Tests | **`tests/`** |
| Projektgedächtnis / Archive | **`memory/`** (Session-Archive, Entscheidungs-Anhänge) |
| Hilfs-Skripte (Migration / Research) | **`scripts/`** |

## Branch- und PR-Disziplin

- Siehe **`Anweisungen.md`** (Git, Commits, Tests) und die Workspace-Regel **`.cursor/rules/PR-WORKFLOW.mdc`**.
- Sobald ein GitHub-PR existiert, endet die erste Zeile der Commit-Message mit **`(#NNN)`** (PR-Nummer).

## Lokales Arbeiten

- **Python:** **3.12.x** (`.python-version`, siehe `pyproject.toml`).
- **Dependency manager:** **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — einmalig installieren, dann im Repo-Root:
  - **`uv sync --extra dev`** (oder **`make bootstrap`**) — legt `.venv/` an und pinned Dependencies aus **`uv.lock`**.
  - **`uv run pytest tests -q`** / **`make test`**
  - **`uv run ruff format app/backend/ti_hub tests`** / **`make fmt`**
  - **`uv run ruff check app/backend/ti_hub tests`** / **`make lint`**
- **Windows:** `make` erfordert eine GNU-Make-Umgebung (z. B. Git Bash, WSL, oder separate Installation).

**Migration:** Root-**`requirements-ci.txt`** und **`pytest.ini`** wurden durch **`pyproject.toml`** + **`uv.lock`** ersetzt (M0.2).
