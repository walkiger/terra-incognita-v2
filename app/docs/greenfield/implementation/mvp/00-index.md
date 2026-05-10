# `implementation/mvp/00-index.md` — MVP-Implementierung: Phasen, Status, Branches

> **Lebendiges Dokument.** Zentraler Steuerungs-Dashboard für die MVP-
> Implementierung. Hier steht, **was als Nächstes kommt**, **wer welche
> Branch hat**, **welche Akzeptanzkriterien gelten** und **wo der Plan
> hingewachsen** ist.
>
> Vor jedem neuen Branch lesen.

---

## Inhalt

1. [Phasen-Modell M0–M8](#1-phasen-modell-m0m8)
2. [Branch- und PR-Konvention](#2-branch--und-pr-konvention)
3. [Akzeptanzkriterien-Standard](#3-akzeptanzkriterien-standard)
4. [Cross-Cutting-Gates (jede Phase)](#4-cross-cutting-gates-jede-phase)
5. [Status-Tabelle (alle Phasen, alle Schritte)](#5-status-tabelle-alle-phasen-alle-schritte)
6. [Definition-of-Done je Phase](#6-definition-of-done-je-phase)
7. [Wie der Index gepflegt wird](#7-wie-der-index-gepflegt-wird)
8. [Querverweise](#8-querverweise)

---

## 1. Phasen-Modell M0–M8

| Phase | Name                    | Ergebnis                                                                | Tag-Bump bei Abschluss |
| ----- | ----------------------- | ----------------------------------------------------------------------- | ---------------------- |
| M0    | Bootstrap & Tooling     | Repo, CI, Compose, Cloudflared, Pre-commit, Branch-Workflow             | `v0.1.0`               |
| M1    | Datenfundament          | SQLite + Migrations + Litestream + R2; Repo-Layer testbar               | `v0.2.0`               |
| M2    | Engine-Protokoll        | NATS-Spine, WS-Engine-Channel, Schema-validiert, Round-Trip-Test        | `v0.3.0`               |
| M3    | Lokale Engine — Skelett | Lauffähige Engine mit Stub-LNN/EBM/KG; pusht Encounter-Events           | `v0.4.0`               |
| M4    | Erste echte Formel      | LNN-State-Update mit `F.LNN.STATE.*`; Engine reagiert auf Tier-Wachstum | `v0.5.0`               |
| M5    | API-Surface             | FastAPI komplett, Auth, Multi-User, OpenAPI frozen                      | `v0.6.0`               |
| M6    | Frontend-Bootstrap      | React + R3F + Live-Stream; 3D-Cockpit erkennbar                         | `v0.7.0`               |
| M7    | Replay & Diagnostik     | Replay-Page, `/diagnostic`, Hybrid-Planner UI durchgereicht             | `v0.8.0`               |
| M8    | Hardening & Deploy      | Cloudflare-Tunnel-Härtung, Multi-User-Smoke, Backup-Restore-Drill       | `v0.9.0` → `v1.0.0`    |

Sequenzielle Reihenfolge ist **nicht** strikt — siehe „Parallelisierungs-
Hinweise" weiter unten. Aber zwei Regeln gelten ausnahmslos:

- **M0 vor allem.** Ohne grünes M0 wird kein Code anderer Phasen
  committed.
- **M2 vor M3.** Engine-Protokoll muss frozen sein, bevor die Engine
  beginnt zu existieren.

### Parallelisierungs-Hinweise

| Parallel möglich | Begründung                                                                         |
| ---------------- | ---------------------------------------------------------------------------------- |
| M1 ↔ M2          | Datenmodell und Event-Log unabhängig (Schreibe-Pfad noch nicht aktiv)              |
| M3 ↔ M5          | Engine-Skelett benötigt nur fixiertes Engine-Protokoll (M2), nicht das volle API   |
| M5 ↔ M6          | Frontend kann gegen API-Mocks gebaut werden, Backend-Routen können parallel reifen |
| M6 ↔ M7          | Replay-Page ist eigenes Frontend-Sub-Modul, kann parallel laufen                   |

### Was NICHT parallel passiert

| Niemals parallel  | Grund                                                    |
| ----------------- | -------------------------------------------------------- |
| M0 ↔ alles andere | Tooling-Rauschen wirft jede andere Arbeit aus dem Tritt  |
| M4 ↔ M3           | M4 baut auf einem stabilen M3-Skelett auf                |
| M8 ↔ alles andere | Deploy-Hardening braucht ein eingefrorenes Komplett-Bild |

---

## 2. Branch- und PR-Konvention

### Branch-Format

```
feature/<kurz-slug>      ← neue Funktionalität (Default für 90 % der Branches)
fix/<kurz-slug>          ← Bugfix
refactor/<kurz-slug>     ← Strukturarbeit ohne neues Verhalten
test/<kurz-slug>         ← reine Test-Erweiterung / Validation-Fix
docs/<kurz-slug>         ← reine Doku
chore/<kurz-slug>        ← Tooling / Dependencies / Config
```

- Slugs sind kurz, kebab-case, sprechend.
- **Keine Phase-Nummern im Branchnamen.** Phase-Mapping passiert
  ausschließlich in dieser Datei.
- **Beispiele:**
  - `feature/event-log-schemas`
  - `feature/sqlite-litestream-bootstrap`
  - `feature/auth-jwt-rs256`
  - `fix/replay-fts-rebuild-debounce`
  - `chore/pre-commit-protected-deletions`

### GitHub-Issues

- **Pro nicht-trivialem Schritt** ein Issue. Trivial = unter 30 Minuten
  geplante Arbeit, einzelne Datei, keine Test-Erweiterung über das
  Selbstverständliche hinaus.
- **Issue-Titel:** identisch zum Slug, ohne Branchpräfix:
  z. B. `event-log-schemas`.
- **Issue-Body:** Akzeptanzkriterien aus dieser Datei kopieren / verlinken.
- **Issue-Labels:** `phase:M0` … `phase:M8`, `tier:contract|impl|test|docs`,
  optional `risk:high`.
- **Issue-Verschluss:** automatisch beim Merge der zugehörigen PR
  (`Closes #NNN` im PR-Body).

Bei sehr kleinen Trivial-Steps gilt: kein Issue, aber Eintrag in der
Status-Tabelle dieser Datei reicht. Ein Branch ohne Issue **muss** in der
PR-Beschreibung diesen Status-Tabellen-Eintrag verlinken.

### PR-Konvention (verbindlich aus `Anweisungen.md` §5 + `PR-WORKFLOW.mdc`)

- PR-Titel = Branch-Slug, präfix-getypt:
  z. B. `feat: event log schemas (#42)` (PR-Nummer wird gleich nach dem
  Anlegen ergänzt — Draft-PR früh öffnen).
- **Pflicht:** Subject-Zeile endet auf `(#NNN)`.
- **Squash-Merge** ist Default. Squash-Title respektiert dieselbe Regel.
- **Pro PR ein Commit** auf `main` nach Squash. Innerhalb des Branchs
  dürfen mehrere Commits liegen — Squash zieht sie zusammen.
- **PR-Body** hat drei Pflicht-Sektionen:

  ```markdown
  ## Summary

  <ein Absatz, was und warum>

  ## Acceptance criteria

  - [x] AC1 (verlinkt auf 00-index.md `Mn.k`)
  - [x] AC2

  ## Test plan

  <Liste der ausgeführten Tests, mit `pytest -k <pattern>` oder UI-Smoke>
  ```

### Cursor-Attribution

`Co-authored-by: Cursor <…>` ist **verboten** (`Anweisungen.md` §5,
`memory/system/constraints.md`). Pre-commit-Hook
`prepare-commit-msg`/`scripts/strip_cursor_coauthor_trailer.py` ist im
Repo aktiv und entfernt den Trailer; jeder Branch-Owner verantwortet,
dass der Hook installiert ist (`pre-commit install --hook-type
prepare-commit-msg`).

### Atomare Commits

- **Eine Änderung = ein Commit** (`Anweisungen.md` §5 _Effiziente
  Ausführung_).
- Mehrere Mini-Commits in einem Stapel sind erlaubt, solange jeder
  einzeln bedeutsam ist.
- Keine „WIP"-Commits in PRs außer in Draft-State; vor Review-Anforderung
  rebase + squash.

---

## 3. Akzeptanzkriterien-Standard

Jeder Schritt-Eintrag (z. B. `M2.3`) hat in seiner Phasen-Datei
(`Mn-*.md`) folgenden Block:

```markdown
### Mn.k — <Slug>

**Branch:** `feature/<slug>`
**Issue:** `#NNN` (oder „—" wenn trivial)
**Vorbedingungen:** Mn.k-1 grün, Mp.q grün, …
**Berührte Pfade:** path1, path2, …
**Formel-Refs:** `F.LNN.STATE.001`, … (oder „—")
**Akzeptanzkriterien:**

1. AC1 — testbar formuliert
2. AC2 — testbar formuliert
   **Tests (neu/erweitert):**

- `tests/.../test_<slug>.py::test_*` (oder konkret)
  **Ressourcen-Budget:** RAM-Limits, CPU-Limits, falls relevant
  **Geschätzte PR-Größe:** ~N Lines diff (≤ 600 ist Ziel)
  **Fertig wenn:** alle AC abgehakt + CI grün + Reviewer-Approve
```

**Mindest-Disziplin:** mindestens **drei** Akzeptanzkriterien pro
Schritt. Nichts vager als „funktioniert" oder „läuft".

---

## 4. Cross-Cutting-Gates (jede Phase)

Diese Gates gelten für **jede** PR, nicht nur ausgewählte:

| Gate                                           | Wann ausgeführt             | Wer                                                 |
| ---------------------------------------------- | --------------------------- | --------------------------------------------------- |
| **Lint / Format**                              | jeder Commit (pre-commit)   | lokal + CI                                          |
| **Type-Check (`mypy --strict`)**               | jeder Push                  | CI                                                  |
| **Pytest (Unit + Integration)**                | jeder Push                  | CI                                                  |
| **Coverage ≥ 80 %** _(neue/geänderte Dateien)_ | jeder Push                  | CI                                                  |
| **Security: `bandit`, `safety`**               | jeder Push                  | CI                                                  |
| **Schema-Linter** (JSON-Schema vs. Pydantic)   | jeder Push                  | CI                                                  |
| **Protected-Deletions-Gate**                   | jeder Push                  | CI (`scripts/check_protected_deletions.py`)         |
| **Doc-Update-Check**                           | bei `feat:`/`refactor:` PRs | CI (sucht passende `Implementierung.*.md`-Änderung) |
| **Cursor-Coauthor-Stripper**                   | jeder Commit                | pre-commit (`prepare-commit-msg`)                   |
| **Health-Smoke** (Compose `up`)                | bei M0/M5/M8 PRs            | CI Job `compose-smoke`                              |
| **Frontend-Smoke** (Playwright minimal)        | bei M6/M7 PRs               | CI Job `web-smoke`                                  |

Alle Gates blockieren den Merge.

### Phasen-spezifische Gates

| Phase | Zusatz-Gate                                                                         |
| ----- | ----------------------------------------------------------------------------------- |
| M2    | NATS-Round-Trip-Integration (`tests/integration/test_nats_roundtrip.py`)            |
| M3    | Engine-Skelett-Conformance-Test (`tests/engine/test_protocol_conformance.py`)       |
| M4    | Formel-Konsistenz-Test (`F.LNN.STATE.*` numerische Vergleiche gegen Referenz-Werte) |
| M5    | OpenAPI-Diff-Gate (Bricht, wenn nicht-additive Schema-Änderung in `/v1/*`)          |
| M6    | Bundle-Größen-Gate (initial JS bundle < 350 kB gz)                                  |
| M7    | Replay-Latenz-Gate (Hybrid-Query p95 < 800 ms auf MVP-Hardware)                     |
| M8    | Memory-Soak-Gate (24 h Compose-Run, kein OOM, RSS-Drift < 5 %)                      |

---

## 5. Status-Tabelle (alle Phasen, alle Schritte)

> **Lesart der Spalten:**
>
> - **Step** — Plan-ID `Mn.k`
> - **Slug** — Branch-Slug
> - **Issue** — GitHub Issue-Nummer (`—` wenn trivial)
> - **Branch** — Branch-Name (mit Präfix)
> - **PR** — PR-Nummer
> - **Status** — `[ ]` offen · `[~]` in Arbeit · `[x]` erledigt · `[!]` blocked · `[?]` unklar
> - **Datum** — Datum des Status-Wechsels auf `[x]` (yyyy-mm-dd)

### M0 — Bootstrap & Tooling

| Step  | Slug                               | Issue | Branch                                   | PR  | Status | Datum      |
| ----- | ---------------------------------- | ----- | ---------------------------------------- | --- | ------ | ---------- |
| M0.1  | repo-greenfield-skeleton           | —     | `chore/repo-greenfield-skeleton`         | —   | [x]    | 2026-05-08 |
| M0.2  | python-pyproject-baseline          | —     | `chore/python-pyproject-baseline`        | 6   | [x]    | 2026-05-09 |
| M0.3  | docker-compose-hub-skeleton        | —     | `feature/docker-compose-hub-skeleton`    | 7   | [x]    | 2026-05-09 |
| M0.4  | docker-compose-vault-skeleton      | —     | `feature/docker-compose-vault-skeleton`  | 8   | [x]    | 2026-05-09 |
| M0.5  | cloudflared-config-hub             | —     | `feature/cloudflared-config-hub`         | 10  | [x]    | 2026-05-09 |
| M0.6  | pre-commit-baseline                | —     | `chore/pre-commit-baseline`              | 10  | [x]    | 2026-05-09 |
| M0.7  | github-actions-ci-baseline         | —     | `chore/github-actions-ci-baseline`       | 10  | [x]    | 2026-05-09 |
| M0.8  | secrets-sops-baseline              | —     | `chore/secrets-sops-baseline`            | 10  | [x]    | 2026-05-09 |
| M0.9  | logging-and-observability-baseline | —     | `feature/logging-observability-baseline` | 10  | [x]    | 2026-05-09 |
| M0.10 | branch-and-pr-rules-md             | —     | `docs/branch-and-pr-rules-md`            | 10  | [x]    | 2026-05-09 |

**Phase:** [x] abgeschlossen am **2026-05-09** · Phase-Tag **`v0.1.0`** _(nach Merge dieser PR setzen und pushen — siehe `M0-bootstrap.md` §5)_

**Phase-Tag bei Abschluss:** `v0.1.0`

### M1 — Datenfundament

| Step  | Slug                                | Issue | Branch                                 | PR  | Status | Datum      |
| ----- | ----------------------------------- | ----- | -------------------------------------- | --- | ------ | ---------- |
| M1.1  | sqlite-baseline-schema              | —     | `feature/sqlite-baseline-schema`       | 5   | [x]    | 2026-05-09 |
| M1.2  | sqlite-fts5-replay-events           | —     | `feature/sqlite-fts5-replay-events`    | 16  | [x]    | 2026-05-09 |
| M1.3  | alembic-migrations-bootstrap        | —     | `feature/alembic-migrations-bootstrap` | 17  | [x]    | 2026-05-09 |
| M1.4  | repository-layer-users              | —     | `feature/repo-users`                   | 20  | [x]    | 2026-05-09 |
| M1.5  | repository-layer-encounters         | —     | `feature/repo-encounters`              | 21  | [x]    | 2026-05-09 |
| M1.6  | repository-layer-replay-events      | —     | `feature/repo-replay-events`           | 22  | [x]    | 2026-05-10 |
| M1.7  | repository-layer-snapshots-manifest | —     | `feature/repo-snapshots-manifest`      | 23  | [x]    | 2026-05-10 |
| M1.8  | litestream-config-hub               | —     | `feature/litestream-config-hub`        | 24  | [x]    | 2026-05-10 |
| M1.9  | r2-bucket-naming-and-iam            | —     | `chore/r2-bucket-naming-and-iam`       | 24  | [x]    | 2026-05-10 |
| M1.10 | vault-r2-pull-worker                | —     | `feature/vault-r2-pull-worker`         | 24  | [x]    | 2026-05-10 |
| M1.11 | restore-drill-script                | —     | `feature/restore-drill-script`         | 24  | [x]    | 2026-05-10 |

**Phase:** [x] abgeschlossen am **2026-05-10** · Phase-Tag **`v0.2.0`** _(nach Merge: `git tag v0.2.0 && git push origin v0.2.0` — Gate siehe `M1-data-foundation.md` §5)_

**Phase-Tag bei Abschluss:** `v0.2.0`

### M2 — Engine-Protokoll

| Step | Slug                           | Issue | Branch                                  | PR  | Status | Datum |
| ---- | ------------------------------ | ----- | --------------------------------------- | --- | ------ | ----- |
| M2.1 | engine-ws-frame-schemas        | —     | `feature/engine-ws-frame-schemas`       | —   | [ ]    |       |
| M2.2 | nats-jetstream-broker-compose  | —     | `feature/nats-jetstream-broker-compose` | —   | [ ]    |       |
| M2.3 | nats-event-log-clients         | —     | `feature/nats-event-log-clients`        | —   | [ ]    |       |
| M2.4 | engine-ws-handshake-and-mtls   | —     | `feature/engine-ws-handshake-and-mtls`  | —   | [ ]    |       |
| M2.5 | engine-ws-roundtrip-tests      | —     | `feature/engine-ws-roundtrip-tests`     | —   | [ ]    |       |
| M2.6 | snapshot-upload-flow           | —     | `feature/snapshot-upload-flow`          | —   | [ ]    |       |
| M2.7 | engine-protocol-version-policy | —     | `docs/engine-protocol-version-policy`   | —   | [ ]    |       |

**Phase-Tag bei Abschluss:** `v0.3.0`

### M3 — Lokale Engine — Skelett

| Step | Slug                              | Issue | Branch                                   | PR  | Status | Datum |
| ---- | --------------------------------- | ----- | ---------------------------------------- | --- | ------ | ----- |
| M3.1 | engine-package-skeleton           | —     | `feature/engine-package-skeleton`        | —   | [ ]    |       |
| M3.2 | engine-cli                        | —     | `feature/engine-cli`                     | —   | [ ]    |       |
| M3.3 | engine-config-and-locale          | —     | `feature/engine-config-and-locale`       | —   | [ ]    |       |
| M3.4 | engine-state-bootstrap            | —     | `feature/engine-state-bootstrap`         | —   | [ ]    |       |
| M3.5 | engine-tick-loop-stub             | —     | `feature/engine-tick-loop-stub`          | —   | [ ]    |       |
| M3.6 | engine-encounter-emitter          | —     | `feature/engine-encounter-emitter`       | —   | [ ]    |       |
| M3.7 | engine-summary-emitter            | —     | `feature/engine-summary-emitter`         | —   | [ ]    |       |
| M3.8 | engine-snapshot-write-stub        | —     | `feature/engine-snapshot-write-stub`     | —   | [ ]    |       |
| M3.9 | engine-protocol-conformance-tests | —     | `test/engine-protocol-conformance-tests` | —   | [ ]    |       |

**Phase-Tag bei Abschluss:** `v0.4.0`

### M4 — Erste echte Formel (LNN-State)

| Step | Slug                               | Issue | Branch                                  | PR  | Status | Datum |
| ---- | ---------------------------------- | ----- | --------------------------------------- | --- | ------ | ----- |
| M4.1 | formula-registry-bootstrap         | —     | `docs/formula-registry-bootstrap`       | —   | [ ]    |       |
| M4.2 | f-lnn-state-001-cfc-update         | —     | `feature/f-lnn-state-001-cfc-update`    | —   | [ ]    |       |
| M4.3 | f-lnn-state-002-tau-modulator      | —     | `feature/f-lnn-state-002-tau-modulator` | —   | [ ]    |       |
| M4.4 | f-lnn-grow-003-tier-emergence      | —     | `feature/f-lnn-grow-003-tier-emergence` | —   | [ ]    |       |
| M4.5 | lnn-step-singleton-entrypoint      | —     | `feature/lnn-step-singleton-entrypoint` | —   | [ ]    |       |
| M4.6 | build-lnn-input-multi-tier         | —     | `feature/build-lnn-input-multi-tier`    | —   | [ ]    |       |
| M4.7 | tier-stable-callback-policy        | —     | `feature/tier-stable-callback-policy`   | —   | [ ]    |       |
| M4.8 | numerical-conformance-suite        | —     | `test/numerical-conformance-suite`      | —   | [ ]    |       |
| M4.9 | engine-summary-now-with-real-state | —     | `feature/engine-summary-real-state`     | —   | [ ]    |       |

**Phase-Tag bei Abschluss:** `v0.5.0`

### M5 — API-Surface

| Step  | Slug                         | Issue | Branch                                 | PR  | Status | Datum |
| ----- | ---------------------------- | ----- | -------------------------------------- | --- | ------ | ----- |
| M5.1  | fastapi-app-skeleton         | —     | `feature/fastapi-app-skeleton`         | —   | [ ]    |       |
| M5.2  | http-health-and-version      | —     | `feature/http-health-and-version`      | —   | [ ]    |       |
| M5.3  | auth-jwt-rs256               | —     | `feature/auth-jwt-rs256`               | —   | [ ]    |       |
| M5.4  | auth-passwords-argon2        | —     | `feature/auth-passwords-argon2`        | —   | [ ]    |       |
| M5.5  | auth-refresh-tokens          | —     | `feature/auth-refresh-tokens`          | —   | [ ]    |       |
| M5.6  | http-encounters-routes       | —     | `feature/http-encounters-routes`       | —   | [ ]    |       |
| M5.7  | http-snapshots-routes        | —     | `feature/http-snapshots-routes`        | —   | [ ]    |       |
| M5.8  | http-replay-timeline-v4-port | —     | `feature/http-replay-timeline-v4-port` | —   | [ ]    |       |
| M5.9  | http-diagnostic-port         | —     | `feature/http-diagnostic-port`         | —   | [ ]    |       |
| M5.10 | http-admin-routes            | —     | `feature/http-admin-routes`            | —   | [ ]    |       |
| M5.11 | ws-viewer-channel            | —     | `feature/ws-viewer-channel`            | —   | [ ]    |       |
| M5.12 | ws-engine-channel            | —     | `feature/ws-engine-channel`            | —   | [ ]    |       |
| M5.13 | rate-limits-and-quotas       | —     | `feature/rate-limits-and-quotas`       | —   | [ ]    |       |
| M5.14 | openapi-freeze-v1            | —     | `docs/openapi-freeze-v1`               | —   | [ ]    |       |

**Phase-Tag bei Abschluss:** `v0.6.0`

### M6 — Frontend-Bootstrap

| Step  | Slug                             | Issue | Branch                                     | PR  | Status | Datum |
| ----- | -------------------------------- | ----- | ------------------------------------------ | --- | ------ | ----- |
| M6.1  | frontend-vite-react-ts-baseline  | —     | `feature/frontend-vite-react-ts-baseline`  | —   | [ ]    |       |
| M6.2  | frontend-auth-flow               | —     | `feature/frontend-auth-flow`               | —   | [ ]    |       |
| M6.3  | frontend-state-mgmt-zustand      | —     | `feature/frontend-state-mgmt-zustand`      | —   | [ ]    |       |
| M6.4  | frontend-ws-viewer-client        | —     | `feature/frontend-ws-viewer-client`        | —   | [ ]    |       |
| M6.5  | frontend-tanstack-query-baseline | —     | `feature/frontend-tanstack-query-baseline` | —   | [ ]    |       |
| M6.6  | frontend-r3f-baseline            | —     | `feature/frontend-r3f-baseline`            | —   | [ ]    |       |
| M6.7  | frontend-r3f-cockpit-skeleton    | —     | `feature/frontend-r3f-cockpit-skeleton`    | —   | [ ]    |       |
| M6.8  | frontend-chat-panel              | —     | `feature/frontend-chat-panel`              | —   | [ ]    |       |
| M6.9  | frontend-tier-panels             | —     | `feature/frontend-tier-panels`             | —   | [ ]    |       |
| M6.10 | frontend-header-counters         | —     | `feature/frontend-header-counters`         | —   | [ ]    |       |
| M6.11 | frontend-csp-and-security        | —     | `feature/frontend-csp-and-security`        | —   | [ ]    |       |
| M6.12 | frontend-i18n-baseline           | —     | `feature/frontend-i18n-baseline`           | —   | [ ]    |       |
| M6.13 | frontend-bundle-size-gate        | —     | `chore/frontend-bundle-size-gate`          | —   | [ ]    |       |

**Phase-Tag bei Abschluss:** `v0.7.0`

### M7 — Replay & Diagnostik

| Step | Slug                             | Issue | Branch                                     | PR  | Status | Datum |
| ---- | -------------------------------- | ----- | ------------------------------------------ | --- | ------ | ----- |
| M7.1 | replay-page-baseline             | —     | `feature/replay-page-baseline`             | —   | [ ]    |       |
| M7.2 | replay-page-hybrid-planner-ui    | —     | `feature/replay-page-hybrid-planner-ui`    | —   | [ ]    |       |
| M7.3 | replay-page-pause-step-controls  | —     | `feature/replay-page-pause-step-controls`  | —   | [ ]    |       |
| M7.4 | replay-page-density-stub         | —     | `feature/replay-page-density-stub`         | —   | [ ]    |       |
| M7.5 | diagnostic-page-baseline         | —     | `feature/diagnostic-page-baseline`         | —   | [ ]    |       |
| M7.6 | diagnostic-page-fts-ops-counters | —     | `feature/diagnostic-page-fts-ops-counters` | —   | [ ]    |       |
| M7.7 | replay-snapshot-load-and-play    | —     | `feature/replay-snapshot-load-and-play`    | —   | [ ]    |       |
| M7.8 | replay-latency-gate              | —     | `chore/replay-latency-gate`                | —   | [ ]    |       |

**Phase-Tag bei Abschluss:** `v0.8.0`

### M8 — Hardening & Deploy

| Step | Slug                         | Issue | Branch                                 | PR  | Status | Datum |
| ---- | ---------------------------- | ----- | -------------------------------------- | --- | ------ | ----- |
| M8.1 | cloudflared-tunnel-hardening | —     | `feature/cloudflared-tunnel-hardening` | —   | [ ]    |       |
| M8.2 | mtls-engine-cert-issuance    | —     | `feature/mtls-engine-cert-issuance`    | —   | [ ]    |       |
| M8.3 | rate-limit-soak-tests        | —     | `test/rate-limit-soak-tests`           | —   | [ ]    |       |
| M8.4 | oom-protection-cgroups       | —     | `chore/oom-protection-cgroups`         | —   | [ ]    |       |
| M8.5 | backup-restore-drill-doc     | —     | `docs/backup-restore-drill`            | —   | [ ]    |       |
| M8.6 | observability-alert-rules    | —     | `feature/observability-alert-rules`    | —   | [ ]    |       |
| M8.7 | multi-user-smoke-suite       | —     | `test/multi-user-smoke-suite`          | —   | [ ]    |       |
| M8.8 | release-v1-checklist         | —     | `docs/release-v1-checklist`            | —   | [ ]    |       |
| M8.9 | tag-v1-0-0                   | —     | `chore/tag-v1-0-0`                     | —   | [ ]    |       |

**Phase-Tag bei Abschluss:** `v0.9.0` (Pre-Release), Final-Tag: `v1.0.0`

---

## 6. Definition-of-Done je Phase

Eine Phase gilt als „grün", wenn:

1. **Alle ihre Schritte** in der Status-Tabelle auf `[x]` stehen.
2. **Phasen-spezifisches Gate** (siehe Tabelle in Sektion 4) erfüllt ist
   und im CI grün ist.
3. **`archive/legacy-docs/Implementierungen.Architektur.md`** ist um die Greenfield-Spalte
   für betroffene Komponenten aktualisiert.
4. **`catchup.md`** hat einen Abschluss-Eintrag mit dem entsprechenden
   `terra-XXX`-Tag (oder einer Greenfield-Session-Nummer wie
   `greenfield-Mn`).
5. **Phase-Tag** ist gepusht: `git tag v0.x.0 && git push --tags`.
6. **Release-Notes** sind in `catchup.md` als Header-Eintrag formatiert.
7. **Onboarding- und Kommando-Doku** (`README.md`, `CONTRIBUTING.md`, **`CLAUDE.md`**) ist mit **CI**, **`Makefile`** und **`pyproject.toml`** abgeglichen — keine widersprüchlichen `pytest`-/`ruff`-Pfaden oder Compose-Hinweise.

---

## 7. Wie der Index gepflegt wird

- **Index + Doku-Bündel (Pflicht je `Mn.k`):** Jede merge-reife PR für einen Index-Schritt aktualisiert **mindestens** diese **`00-index.md`**-Zeile (`[x]`, Datum, PR-Nummer) **und** die **Phasendatei** (`M0-bootstrap.md`, `M1-data-foundation.md`, … — Abschnitt **„Erledigte Änderungen“** bzw. Stand-Zeile am Ende). Ändern sich Kommandos, Pfade oder Workflows, gehören **`CONTRIBUTING.md`**, **`CLAUDE.md`** und/oder **`README.md`** **in derselben PR** mit — nicht auf einen Folge-PR verschieben.
- **Bei jedem Mergen einer Greenfield-PR:** Status-Eintrag aktualisieren
  (`[x]`, Datum, PR-Nummer, ggf. Issue-Nummer). Eintrag zusätzlich in
  der Phasen-Datei als „Erledigte Änderungen" markieren.
- **Bei Plan-Änderungen** (neuer Schritt, Streichung, Umordnung):
  separate `docs/...`-PR mit Begründung. Diese PR ist klein, nur Doku,
  hat aber denselben PR-Workflow durchlaufen.
- **Am Abschluss einer ganzen Phase Mn** (alle Schritte dieser Phase in der
  Status-Tabelle `[x]`, Phase „grün" nach **§6**): verpflichtend in **derselben
  Phase oder unmittelbar folgenden PR(s)**:
  1. §6 Punkt 1–7 erfüllen (inkl. Tag, `catchup.md`, Architektur-Spalte).
  2. Phasen-**Gate** in der jeweiligen Phasen-Datei (`M0-bootstrap.md`, …)
     gegen den Ist-Stand prüfen und Texte anpassen.
  3. **`memory/system/decisions.md`** um Phase-Abschluss / Policy-Änderungen
     ergänzen (mit Datum).
  4. **`.agent-os/pr-spec.json`** auf den nächsten Arbeitspaket-Kontext setzen
     (oder bewusst leeren Platzhalter dokumentieren).
  5. Repo-Root- und Greenfield-Einstiegs-Doku aktualisieren, falls sich
     Workflows geändert haben (**§6 Nr. 7**).
- **Bei Phasen-Abschluss:** Header der Status-Tabelle wird mit
  `[x] abgeschlossen am yyyy-mm-dd, Tag v0.x.0` ergänzt.

**Prinzip:** Diese Datei lügt nie. Wenn der Status hier `[x]` ist, dann
ist die Arbeit nachweislich gemerged und das CI grün.

---

## 8. Querverweise

- Phasen-Detail-Dateien: `M0-bootstrap.md`, `M1-data-foundation.md`,
  `M2-engine-protocol.md`, `M3-local-engine-skeleton.md`,
  `M4-first-formula-lnn-state.md`, `M5-api-surface.md`,
  `M6-frontend-bootstrap.md`, `M7-replay-diagnostics.md`,
  `M8-hardening-deploy.md`
- Architektur: `../architecture/mvp.md`, `../architecture/production.md`
- Glossar: `../00-glossary.md`
- Formel-Registry: `../formulas/registry.md`
- Lookup-Vertrag: `../protocols/pdf-lookup.md`
- Regelwerk: `Anweisungen.md`, `.cursor/rules/PR-WORKFLOW.mdc`,
  `.cursor/rules/NO-SILENT-DELETIONS.mdc`,
  `.cursor/rules/MODEL-SWITCHING-PROTOCOL.mdc`,
  `.cursor/rules/SUBAGENT-DELEGATION-FALLBACK.mdc`

---

_Stand: 2026-05-10 · Status: Phase **M0** abgeschlossen (`v0.1.0`) · Phase **M1** abgeschlossen (`v0.2.0` Tag nach Merge setzen) · nächster Schritt **M2.1** (`feature/engine-ws-frame-schemas`) · Hub-API-Stubs unter `app/backend/api/` (u. a. nach PR #18)_
