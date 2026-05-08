# `app/docs/greenfield/CHANGELOG.md` — Greenfield-Plan-Versionsspur

> **Zweck.** Lebendiger Änderungsprotokoll-Zwilling zum
> Greenfield-Plan. Während die Implementierung von v0.1.0 → v1.0.0
> wandert, wird hier *jede* nicht-triviale Änderung an Plan und
> Verträgen festgehalten.
>
> Versionierung folgt SemVer:
>
> * **MAJOR** — Bruch im Vertrag (z.B. v1 → v2 OpenAPI-Schema).
> * **MINOR** — additive Erweiterung von Verträgen oder neue
>   Implementierungs-Phase.
> * **PATCH** — Klarstellungen, Tippfehler, Dokumentations-Tuning.
>
> Datum-Format: ISO-8601 (`YYYY-MM-DD`).

---

## Persistenz‑Kanone & Agent‑Memory — 2026-05-08

* **v1.0 Hub‑Persistenz = SQLite + Litestream** (ADR‑000 / ADR‑001); **kein DuckDB** auf dem Greenfield‑Implementierungspfad unter **`app/`**.
* DuckDB taucht nur noch als **historische / Legacy‑Referenz** (Root‑Docs wie `docs/ARCHITECTURE.md`, optionales lokales `archive/`) auf.
* Abgleich: `memory/system/decisions.md`, `memory/system/decisions-archive-persistence-duckdb-era.md` (Skalierungs‑Anhang), `memory/agents/orchestrator.md`, `memory/runtime/open-issues.md`, `memory/session/catchup-archive-legacy-sessions.md` (terra‑Historie), `CLAUDE.md`, `.agent-os/pr-spec.json`.
* **Doc‑Größe:** Root **`catchup.md`** enthält nur aktuelle Policy‑/Research‑Einträge; ältere **terra-***-Sessions liegen im Archiv oben.
* **M0.1 Layout:** Produkt‑Stubs **`app/{backend,engine,web,packages}`** + **`deploy/{compose,ansible}`** + **`secrets/`** (Stub); Spezifikation in **`implementation/mvp/M0-bootstrap.md`** angeglichen.

---

## Repo layout — 2026-05-09

* **Pfad:** gesamter Greenfield-Baum liegt unter **`app/docs/greenfield/`**
  (vorher `docs/greenfield/`).
* **Stub:** `docs/greenfield/README.md` verweist auf den neuen Pfad (alte Links).
* **Neu:** `app/README.md` (Produkt-root), `archive/README.md` (Legacy-Policy),
  `architecture/truth-anchors-and-ghosts.md` (Truth Anchors, Seeds→Geist).
* **Agent:** `.cursor/agents/pdf-lookup-protocol.md` zeigt kanonisch auf
  `app/docs/greenfield/protocols/pdf-lookup.md`.

---

## Legacy freeze — 2026-05-09

* Laufwagen (**`backend/`**, **`frontend/`**, **`tests/`**, Docker/Compose,
  **`requirements*.txt`**, **`pytest.ini`**, Legacy-**`README.md`**) liegt unter
  **`archive/legacy-terra/`** (siehe `archive/README.md`).
* Alle **`Implementierung.*.md`** und **`Implementierungen.Architektur.md`** liegen
  unter **`archive/legacy-docs/`**.
* Root **`pytest.ini`** + **`README.md`** sind Greenfield-first mit Legacy-Pointern;
  CI-Workflows (Tests/Docker/Agent‑CI) nutzen die verschobenen Pfade.

---

## [0.0.0] — 2026-05-08 — Initial Greenfield-Plan

* **Hinzugefügt** — Greenfield-Plan-Skelett:
  * `README.md`, `00-glossary.md`,
  * `architecture/{mvp,production,data-model,security,observability}.md`,
  * `implementation/{mvp/00-index, M0–M8, production}.md`,
  * `formulas/{README,registry}.md`,
  * `protocols/{pdf-lookup,replay-contract,snapshot,event-log}.md`,
  * `runbooks/{disaster-recovery,oom-and-capacity,operations}.md`,
  * `decisions/{README,000-baseline,001-sqlite-litestream,002-nats-jetstream,003-engine-mtls}.md`,
  * `contracts/openapi-v1-summary.md`,
  * `.cursor/agents/pdf-lookup-protocol.md` (Pseudo-Subagent).
* **Verträge eingefroren**:
  * `replay_timeline_window_v4` (siehe `protocols/replay-contract.md`).
  * `snapshot.format_version = v1.0.0` (siehe `protocols/snapshot.md`).
  * NATS-Subjekt­namen (`engine.events.*`,
    `engine.heartbeat.*`, `replay.window.*`,
    `system.audit.*`).
  * Cookies (`HttpOnly`, `SameSite=Strict`, `Secure`).
* **Pfad** — Pfad B (Thin-Shell auf 2× AMD Micro Free Tier) als
  v1.0-Lock-In, M4-Vollausbau als v2.0-Ziel.
* **Lookup-Protokoll** — drei Pfade (Direkt-`Grep`,
  `explore`-Subagent, `research-agent`-Extraktion).
* **Hinweis** — der canonical Hasani-2022-CfC-Paper fehlt
  derzeit im Korpus; Extraktion in M4.1 vorgemerkt.

---

## [Unreleased] — Planned changes

* SQLite-/Hub-Schema: Tabellen für **API-/Seed-Evidence**, **Ghost-Materialisierung**,
  **Fetcher-Jobs** (Dedupe, Quota, Lineage) — konkret in M1.x nachziehen.
* `runbooks/multi-user-onboarding.md` — Pfad für die ersten
  „echten" Beta-User der v1.0-Phase.
* M4.1 — Hasani-2022-CfC-Paper extrahieren (`research-agent`).
* `decisions/004-replay-hybrid-frozen.md`, …,
  `decisions/013-engine-pool-topology.md` — Inhalte aus
  `decisions/README.md`-Index.
* `architecture/observability.md` §11 — Akzeptanzkriterien
  für Synthetic-Checks, sobald Vault-VM provisioniert ist.

---

## Versionsfahrplan (Erinnerung)

| Tag       | Bedeutung                                                              |
|-----------|-------------------------------------------------------------------------|
| `v0.1.0`  | M0 + M1 + M2 zusammengeführt; Engine-Protokoll eingefroren              |
| `v0.2.0`  | M3 abgeschlossen; Engine-Skeleton kann sich verbinden                   |
| `v0.3.0`  | M4 abgeschlossen; erster `F.*`-Eintrag verifiziert                      |
| `v0.4.0`  | M5 abgeschlossen; OpenAPI v1 eingefroren                                |
| `v0.5.0`  | M6 abgeschlossen; Frontend-Bootstrap deployed                           |
| `v0.6.0`  | M7 abgeschlossen; Replay-Page voll funktional                           |
| `v0.7.0`  | M8 abgeschlossen; Hardening + Deploy-Drill durch                        |
| `v1.0.0`  | öffentlicher MVP-Launch                                                  |
| `v1.x.y`  | Iteratives Härten + Bug-Fixes + Mini-Feature-Adds                        |
| `v2.0.0`  | M4-Vollausbau (siehe `implementation/production.md`)                     |

---

*Stand: 2026-05-09 · Pfad `app/docs/greenfield/`*
