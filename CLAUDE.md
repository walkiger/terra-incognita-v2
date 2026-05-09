# CLAUDE.md — Orientierung (terra-incognita-v2)

> Kurzfassung für Sessions in diesem **Greenfield**-Repo (bewusst ohne Legacy-Tree).

---

## Repo und Zweck

**Repo:** https://github.com/walkiger/terra-incognita-v2

**Inhalt:** Thin-Shell-MVP-Planung und späterer Produktcode unter **`app/`**. Kein geklonter Monolith-Stand aus **terra-incognita** — bei Bedarf dort oder lokal nachschlagen.

---

## Wo du anfängst

1. [`README.md`](README.md) — Überblick
2. [`app/README.md`](app/README.md) — Produkt-Root
3. [`app/docs/greenfield/README.md`](app/docs/greenfield/README.md) — Lesepfad MVP M0–M8
4. [`memory/README.md`](memory/README.md) — Session-/System-Archive (Legacy‑Kontinuität zeigt auf **`walkiger/terra-incognita`**)

Git-/Agent-Disziplin: **`Anweisungen.md`** und **`.cursor/rules/`**.

---

## Tests (heute)

```text
uv sync --extra dev
uv run pytest tests -q -m "not compose_hub and not compose_vault and not compose_observability"
```

Voller Integration/Docker-Lauf (CI **`compose-smoke`**):
`uv run pytest tests/integration -q -m "compose_hub or compose_vault or compose_observability"`
Details und **ruff**: **`CONTRIBUTING.md`**. Ohne globales `uv`: `py -m pip install uv` und dann `py -m uv sync --extra dev`.

Windows: siehe **`CONTRIBUTING.md`** (`py`, nicht `python3`).
