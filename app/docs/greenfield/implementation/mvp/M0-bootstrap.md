# `M0-bootstrap.md` — Phase M0: Bootstrap & Tooling

> **Lebendiges Dokument.** Ergebnis: Ein laufendes Repo, in dem alle
> Folgephasen committen können — mit grünem CI, mit Compose-Stacks,
> mit Cloudflare-Tunnel, mit Pre-commit-Hooks, mit dokumentierter
> Branch- und PR-Disziplin.
>
> **Phase-Tag bei Abschluss:** `v0.1.0`

---

## Inhalt

1. [Phasen-Ziel](#1-phasen-ziel)
2. [Vorbedingungen](#2-vorbedingungen)
3. [Architektur-Bezug](#3-architektur-bezug)
4. [Schritte M0.1 – M0.10](#4-schritte-m01--m010)
5. [Phasen-Gate](#5-phasen-gate)
6. [Erledigte Änderungen](#6-erledigte-änderungen)

---

## 1. Phasen-Ziel

Wir wollen am Ende von M0 in der Lage sein, **jede beliebige Folgephase**
mit demselben Tooling-Erlebnis zu beginnen. Konkret:

- Ein `git clone` + `make bootstrap` reicht für einen lauffähigen
  Dev-Stand.
- `docker compose -f deploy/compose/hub.yml --profile minimal up` startet
  einen Hub-Stack lokal, der mit dem Cloudflare-Tunnel-Pfad identisch ist.
- `pre-commit` blockiert lokal alle Commit-Hygiene-Verstöße (Cursor-
  Co-Author, Protected-Deletions, Lint, Schema).
- GitHub-Actions führt bei jedem Push die Pflicht-Gates aus (Sektion 4
  von `00-index.md`).
- Cloudflare-Tunnel ist auf VM-A produktiv — `https://<hub-host>/v1/health`
  liefert das echte Health-JSON aus dem laufenden Compose-Stack.

**Was M0 _nicht_ tut:**

- Keine Datenbank-Schemas (das ist M1).
- Keine API-Routen außer `/v1/health` und `/v1/version`.
- Kein Frontend-Build außer Caddy-Statisch-Default-Page.
- Kein Auth.

---

## 2. Vorbedingungen

- GitHub-Repo `walkiger/terra-incognita` ist vorhanden.
- Cloudflare-Account hat einen Tunnel mit Zone konfiguriert; Tunnel-
  Credentials liegen lokal vor.
- Oracle-Cloud: 2× AMD Micro VMs sind installiert mit Ubuntu 24.04 LTS
  (oder gleichwertig), `cloudflared` ist installiert (Stand 2026-05-08
  bestätigt).
- Lokaler Entwicklungsrechner hat Docker, Python 3.12, Node 22 LTS und
  `git`.

---

## 3. Architektur-Bezug

Phase M0 implementiert die **Tooling-Schicht** der Architektur, die in
[`../../architecture/mvp.md`](../../architecture/mvp.md) Sektion 11
beschrieben ist.

Querverweise:

- `architecture/mvp.md` §4 — Service-Inventar (Bestätigung der Image-Choices)
- `architecture/mvp.md` §11 — Deployment (Image-Build, Compose, Ansible)
- `Anweisungen.md` §2 — Coding-Standards (Python 3.12, type hints, async/await)
- `Anweisungen.md` §5 — Git-Regeln, Commit-Format
- `.cursor/rules/PR-WORKFLOW.mdc`
- `.cursor/rules/NO-SILENT-DELETIONS.mdc`
- `.cursor/rules/MODEL-SWITCHING-PROTOCOL.mdc`

---

## 4. Schritte M0.1 – M0.10

---

### M0.1 — repo-greenfield-skeleton

**Branch:** `chore/repo-greenfield-skeleton`
**Issue:** `—` (trivial)
**Vorbedingungen:** keine
**Berührte Pfade:**

```
.
├── README.md                          ← überarbeiten (Greenfield-Hinweis)
├── CONTRIBUTING.md                    ← neu (Verweis auf app/docs/greenfield)
├── pyproject.toml                     ← M0.2
├── package.json                       ← M0.2 (Frontend unter app/web)
├── Makefile                           ← neu (bootstrap, test, fmt, lint)
├── deploy/compose/                    ← neu, leer (M0.3 / M0.4)
├── deploy/ansible/                    ← neu, leer
├── secrets/                           ← neu, .gitkeep + .gitignore-Eintrag
├── app/backend/                       ← neu, leer (Hub FastAPI später, M5+)
├── app/engine/                        ← neu, leer (Local Engine später, M3+)
├── app/web/                           ← neu, leer (Vite/React später, M6)
├── app/packages/                      ← neu, leer (geteilte Pakete — Roadmap)
└── tests/                             ← neu (`__init__.py` + Layout-Tests)
```

**Hinweis:** Produktcode und spätere Compose-Build-Contexts liegen unter **`app/`**; Deploy-/Infra-Bäume bleiben unter **`deploy/`** am Repo-Root (vgl. [`app/README.md`](../../../../README.md)).

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `git ls-files` listet **`app/backend`**, **`app/engine`**, **`app/web`**, **`app/packages`**, **`deploy/compose`**, **`deploy/ansible`**, **`secrets`** jeweils mit mindestens einer Stub-Datei (typisch `.gitkeep`) sowie **`tests/__init__.py`**.
2. `README.md`-Header verlinkt prominent `app/docs/greenfield/README.md`.
3. `CONTRIBUTING.md` hat eine Sektion **„Vor jedem Code-Beitrag"** mit
   den Lese-Schritten aus `app/docs/greenfield/README.md`.
4. `Makefile` hat mindestens die Targets `bootstrap`, `test`, `fmt`,
   `lint`, `compose-hub`, `compose-vault`. Jedes Target druckt vorne
   einen Banner-Echo, was es tut.

**Tests (neu/erweitert):**

- `tests/test_repo_layout.py::test_required_directories_exist`
- `tests/test_repo_layout.py::test_makefile_targets_present`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~150 Lines diff
**Fertig wenn:** alle AC + CI grün + Reviewer-Approve.

---

### M0.2 — python-pyproject-baseline

**Branch:** `chore/python-pyproject-baseline`
**Issue:** `—` (trivial)
**Vorbedingungen:** M0.1 gemerged
**Berührte Pfade:** `pyproject.toml`, `requirements*.txt` _(falls vorhanden, ablösen)_, `.python-version`, `app/engine/pyproject.toml` (separates Sub-Paket)

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `pyproject.toml` deklariert Python 3.12 als Mindestversion (`requires-python = ">=3.12,<3.13"` für Hub; Engine darf später 3.13t freigeben — getrennt).
2. Dependency-Manager ist **`uv`**. `uv.lock` wird committed.
3. Linter / Formatter sind **`ruff`** (Lint + Format), Konfiguration im `pyproject.toml`. Keine separaten `flake8` / `black` / `isort`.
4. `mypy --strict` ist aktiviert; `pyproject.toml` hat den Block `[tool.mypy]`.
5. `pytest` + `pytest-asyncio` + `pytest-cov` + `coverage` sind als Dev-Deps gepinnt.
6. `make test` führt `uv run pytest -q` mit demselben Ausschluss der Docker-Compose-Smoke-Marker wie CI aus (`-m "not compose_hub and not compose_vault"`).
7. Es gibt **kein** `requirements.txt` mehr; Migrationspfad in PR-Body dokumentiert.

**Tests (neu/erweitert):**

- `tests/test_tooling.py::test_pyproject_python_constraint`
- `tests/test_tooling.py::test_ruff_config_present`
- `tests/test_tooling.py::test_mypy_strict_config_present`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~200 Lines diff
**Fertig wenn:** AC erfüllt, `make bootstrap && make test` lokal grün, CI-Workflow „lint" und „type-check" grün.

---

### M0.3 — docker-compose-hub-skeleton

**Branch:** `feature/docker-compose-hub-skeleton`
**Issue:** `#NNN` (Issue eröffnen — Service-Auswahl ist diskussionswürdig)
**Vorbedingungen:** M0.1 gemerged
**Berührte Pfade:**

```
deploy/
├── compose/
│   ├── hub.yml                         ← neu, Haupt-Datei
│   ├── hub.override.dev.yml            ← Dev-Overlays (lokale Volumes)
│   └── env.example                     ← Beispiel-Variablen
├── caddy/Caddyfile.hub                 ← neu, minimal
├── api/Dockerfile                      ← neu, multi-stage
└── api/requirements-runtime.txt         ← runtime-only Pins
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `hub.yml` definiert **mindestens** die Services: `caddy`, `api`, `nats`, `cloudflared`, `prom-node-exporter`. Jeder Service hat:
   - `image:` (eigenes Image für `api`, public für andere)
   - `mem_limit:` und `mem_reservation:`
   - `restart: unless-stopped`
   - `oom_score_adj:` (siehe Sektion „OOM" weiter unten)
   - `healthcheck:` (mindestens `curl -fsS .../health` oder Service-spezifisch)
   - `logging:` mit `driver: json-file`, `max-size: 10m`, `max-file: "3"`
2. Compose-Profile sind aktiv:
   - `default` — alle Services
   - `minimal` — ohne `prom-node-exporter`, ohne Grafana (Grafana kommt in M0.9)
3. `api`-Image ist multi-stage:
   - Stage 1: `python:3.12-slim` mit `uv` als Builder, installiert Dependencies in `/opt/venv`.
   - Stage 2: `python:3.12-slim` distroless-ähnlich, kopiert `/opt/venv` und Code, läuft als nicht-root-User `terra` (UID 10001).
4. `api`-Container exponiert nur `8000`, `caddy` exponiert nichts nach außen — Anbindung erfolgt über `cloudflared` an Cloudflare-Edge.
5. `docker compose -f hub.yml --profile minimal up -d` läuft lokal ohne Fehler. `curl localhost:80/v1/health` antwortet (über Caddy proxy auf api).
6. `api`-Health-Endpoint ist **stub**, antwortet `{"ok": true, "version": "0.0.1-bootstrap"}`. Vollständiges Health-Schema wird in M5 finalisiert.
7. `mem_limit` der Services in Summe ≤ 720 MB für Profil `minimal`.

**OOM-Reihenfolge** (`oom_score_adj` höher = wird zuerst gekillt):

- `prom-node-exporter`: +500
- `cloudflared`: +200
- `nats`: 0
- `api`: -100
- `caddy`: -200

**Tests (neu/erweitert):**

- `tests/integration/test_compose_hub_smoke.py::test_compose_minimal_brings_up`
  - benutzt `docker-compose-py` oder `pytest-docker-compose`
  - Skip-Marker, falls Docker nicht verfügbar
- `tests/integration/test_compose_hub_smoke.py::test_health_endpoint_through_caddy`

**Ressourcen-Budget:** Compose-Profile `minimal` bleibt < 720 MB RAM-Reservierung total.
**Geschätzte PR-Größe:** ~400 Lines diff
**Fertig wenn:** AC erfüllt, lokale Smoke-Test grün, CI-Job `compose-smoke` grün.

---

### M0.4 — docker-compose-vault-skeleton

**Branch:** `feature/docker-compose-vault-skeleton`
**Issue:** `#NNN`
**Vorbedingungen:** M0.3 gemerged
**Berührte Pfade:**

```
deploy/
├── compose/vault.yml
├── compose/vault.override.dev.yml
├── caddy/Caddyfile.vault
└── workers/r2-pull/                    ← Stub-Image, pflanzt nur Disk-Layout
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `vault.yml` definiert Services: `caddy`, `cloudflared`, `prom-node-exporter`, `r2-pull` (Stub).
2. `r2-pull` ist im M0 nur ein **Stub-Container** mit Loop `sleep 3600`. Echte Logik kommt in M1.10.
3. Compose-Profile:
   - `default` — alle Services
   - `minimal` — ohne `prom-node-exporter`
4. `mem_limit`-Summe ≤ 480 MB für Profil `minimal`.
5. `caddy` serviert eine Default-Seite `/` mit Status-JSON (Vault-Heartbeat).
6. Lokal: `docker compose -f deploy/compose/vault.yml -f deploy/compose/vault.override.dev.yml --profile minimal up -d` läuft fehlerfrei (alle Vault-Services sind profilisiert; ohne `--profile` startet nichts).

**Tests:**

- `tests/integration/test_compose_vault_smoke.py::test_compose_brings_up`
- `tests/integration/test_compose_vault_smoke.py::test_caddy_default_page`

**Ressourcen-Budget:** ≤ 480 MB im Profil `minimal`.
**Geschätzte PR-Größe:** ~180 Lines diff
**Fertig wenn:** AC erfüllt + CI grün.

---

### M0.5 — cloudflared-config-hub

**Branch:** `feature/cloudflared-config-hub`
**Issue:** `#NNN`
**Vorbedingungen:** M0.3 gemerged
**Berührte Pfade:**

```
deploy/cloudflared/
├── config.hub.yml                       ← Tunnel-Routing
├── config.vault.yml                     ← Tunnel-Routing
└── README.md                             ← Setup-Schritte (manuell)
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `config.hub.yml` routet:
   - `terra.<example>.tld` → `http://api:8000`
   - `app.terra.<example>.tld` → `http://caddy:80`
2. `config.vault.yml` routet:
   - `mirror.app.terra.<example>.tld` → `http://caddy:80`
3. Beide Configs sind **per Hostname kommentiert** mit dem Zweck.
4. `deploy/cloudflared/README.md` dokumentiert exakt:
   - Wie der Cloudflare-Tunnel auf der VM einmalig erstellt wurde (`cloudflared tunnel create ...`).
   - Wo die Credentials liegen (in welchem Volume).
   - Wie ein Wechsel der Tunnel-ID gemanagt wird.
5. `cloudflared`-Service in `hub.yml` mountet `/etc/cloudflared` korrekt.
6. **Acceptance-Smoke (manuell):** `https://terra.<example>.tld/v1/health` antwortet aus dem Hub-API.

**Tests:**

- `tests/integration/test_cloudflared_config_lint.py::test_config_yaml_parses`
- `tests/integration/test_cloudflared_config_lint.py::test_no_duplicate_hostnames`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~120 Lines diff
**Fertig wenn:** AC erfüllt + manueller Smoke ok + CI grün.

---

### M0.6 — pre-commit-baseline

**Branch:** `chore/pre-commit-baseline`
**Issue:** `—` (trivial)
**Vorbedingungen:** M0.2 gemerged
**Berührte Pfade:** `.pre-commit-config.yaml`, `scripts/check_protected_deletions.py` (falls noch nicht existent), `scripts/strip_cursor_coauthor_trailer.py` (Bestand prüfen)

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `.pre-commit-config.yaml` aktiviert:
   - `ruff-format` + `ruff-check`
   - `prettier` für `*.md` / `*.yaml` / `*.json` / `*.tsx` / `*.ts`
   - `check-protected-deletions` (lokaler Hook → `scripts/check_protected_deletions.py`)
   - `strip-cursor-coauthor-trailer` (lokaler `prepare-commit-msg`-Hook)
   - `check-yaml`, `check-json`, `end-of-file-fixer`, `trailing-whitespace`
   - `mypy` (optional, kann teuer sein — als `language: system` opt-in)
2. `pre-commit install --hook-type pre-commit --hook-type prepare-commit-msg` ist im `Makefile`-Target `bootstrap` enthalten.
3. `scripts/check_protected_deletions.py` ist vollständig, deckt die Pfade aus `.cursor/rules/NO-SILENT-DELETIONS.mdc` ab, hat eigene Tests in `tests/test_check_protected_deletions.py`.
4. `scripts/strip_cursor_coauthor_trailer.py` entfernt zuverlässig die Zeile `Co-authored-by: Cursor <cursoragent@cursor.com>` aus jeder Commit-Message-Position.

**Tests:**

- `tests/test_check_protected_deletions.py::test_blocks_unapproved`
- `tests/test_check_protected_deletions.py::test_allows_approved`
- `tests/test_strip_cursor_coauthor.py::test_removes_trailer_when_present`
- `tests/test_strip_cursor_coauthor.py::test_idempotent_when_absent`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~180 Lines diff
**Fertig wenn:** Hook lokal installiert, ein Test-Commit mit Co-Author-Trailer wird sauber gestrippt, CI-Job `pre-commit-ci` grün.

---

### M0.7 — github-actions-ci-baseline

**Branch:** `chore/github-actions-ci-baseline`
**Issue:** `#NNN`
**Vorbedingungen:** M0.6 gemerged
**Berührte Pfade:**

```
.github/workflows/
├── ci.yml                              ← Haupt-Workflow
├── ci-build-images.yml                 ← nur Build (Tag-Trigger)
├── cd-release.yml                      ← Release-Notes + GHCR-Push
└── nightly-soak.yml                    ← Nächtlicher Compose-Soak
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `ci.yml` läuft auf jedem `push` und `pull_request`:
   - Job `lint` — `ruff format --check`, `ruff check`
   - Job `type-check` — `mypy --strict backend engine`
   - Job `test` — `pytest -q --cov` (Coverage-Report-Artifact)
   - Job `schema-lint` — JSON-Schemas vs. Pydantic-Modelle abgleichen
   - Job `protected-deletions` — `python scripts/check_protected_deletions.py --pr-base ${{ github.base_ref }}`
   - Job `compose-smoke` (`needs: lint, test`) — bringt `hub.yml --profile minimal` hoch, prüft `/v1/health`
2. Caching: `uv`-Cache, Docker-Layer-Cache.
3. Artifacts: Coverage-Report, Compose-Logs (bei Fehler).
4. Branch-Protection-Regeln (über GitHub-UI dokumentiert in PR-Body):
   - Required Checks: `lint`, `type-check`, `test`, `schema-lint`, `protected-deletions`, `compose-smoke`
   - Linear History, Squash-Merge, Required Reviews ≥ 1.
5. `nightly-soak.yml` läuft `cron 0 3 * * *` UTC, baut hub-Stack, lässt 60 Minuten Heartbeat-Last laufen, prüft RSS-Drift.

**Tests:** Workflow-Validität wird durch erfolgreichen Lauf bewiesen — kein zusätzlicher Pytest.

**Ressourcen-Budget:** CI-Job-RAM ≤ 2 GB pro Step (GitHub-Hosted-Runner-Limit).
**Geschätzte PR-Größe:** ~350 Lines diff
**Fertig wenn:** Erste PR nach Merge zeigt alle Checks grün; Branch-Protection ist aktiv.

---

### M0.8 — secrets-sops-baseline

**Branch:** `chore/secrets-sops-baseline`
**Issue:** `#NNN`
**Vorbedingungen:** M0.7 gemerged
**Berührte Pfade:**

```
secrets/
├── .gitignore                            ← *.unencrypted.*
├── .sops.yaml                            ← AGE-Recipient-Konfig
├── hub.sops.yaml                          ← verschlüsselte Hub-Secrets (Beispiel-Schema)
└── README.md                              ← Setup-Schritte (key gen, decrypt)
docs/
└── operations/secrets.md                  ← Wie Schlüssel rotiert werden
deploy/
└── ansible/group_vars/all/vault.yml.example ← Vorlage
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `sops` wird mit **AGE**-Recipient-Schema konfiguriert (kein PGP).
2. `secrets/hub.sops.yaml` enthält Beispielfelder (`POSTGRES_PASSWORD`, `JWT_PRIVATE_KEY`, …) — alle Werte verschlüsselt.
3. `secrets/.gitignore` blockt `*.unencrypted.*`.
4. CI hat einen Job `secrets-lint`, der prüft:
   - Keine Klartext-Geheimnisse im Repo (regex-Heuristik mit `gitleaks` oder `trufflehog` als CI-Step).
   - `secrets/.sops.yaml` ist syntaktisch valide.
5. `docs/operations/secrets.md` dokumentiert **End-to-End**: AGE-Key auf einem neuen Dev-Rechner installieren, Secrets entschlüsseln, neuen Recipient hinzufügen, Recipient entfernen, Notfall-Rotation.
6. Integration mit Compose: Compose-Files lesen Secrets aus dem entschlüsselten `.env`-File, das beim Bootstrap generiert wird (siehe Makefile-Target `secrets-decrypt`).

**Tests:**

- `tests/test_secrets_layout.py::test_no_unencrypted_files_committed`
- `tests/test_secrets_layout.py::test_sops_config_present`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~220 Lines diff
**Fertig wenn:** Lokales `make secrets-decrypt` produziert `secrets/hub.env` mit allen erwarteten Variablen; CI grün.

---

### M0.9 — logging-and-observability-baseline

**Branch:** `feature/logging-observability-baseline`
**Issue:** `#NNN`
**Vorbedingungen:** M0.3 gemerged, M0.4 gemerged
**Berührte Pfade:**

```
deploy/compose/hub.yml                  ← Prom + Grafana-Service hinzufügen
deploy/prometheus/
├── prometheus.yml
├── alert_rules.example.yml
└── README.md
deploy/grafana/
├── provisioning/datasources/prom.yml
├── provisioning/dashboards/dashboards.yml
└── dashboards/
    ├── hub-health.json
    ├── hub-api.json
    ├── hub-realtime.json (Stub)
    ├── hub-replay.json (Stub)
    └── hub-persistence.json (Stub)
backend/api/observability.py              ← Prom-Client-Init
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `prom-server` und `grafana`-Services in `hub.yml` sind aktiv im Default-Profil, **abschaltbar** über `--profile minimal` (für RAM-knapp-Fälle).
2. Prom scrapt: `prom-node-exporter`, `api` (eigener `/metrics`-Endpunkt), `cloudflared` (falls Metriken-Endpoint aktiviert), `nats` (Built-in `/varz`/`/jsz` mit Adapter).
3. Grafana hat **Stub**-Dashboards für die fünf in `architecture/mvp.md` §10 benannten Boards (Hub Health, Hub API, Hub Realtime, Hub Replay, Hub Persistence). Inhalt vorerst Platzhalter-Panels — vervollständigt in den Phasen, in denen die jeweiligen Metriken existieren.
4. `backend/api/observability.py` registriert Prom-Counter / Histogramme zentral; `api` exposed `/metrics` (Bearer-protected mit einem statischen Token aus `secrets/`).
5. `alert_rules.example.yml` ist nicht aktiv, aber dokumentiert die in `architecture/mvp.md` §10 genannten Alerts.

**Tests:**

- `tests/test_observability_module.py::test_metrics_endpoint_responds`
- `tests/test_observability_module.py::test_metrics_exposes_minimum_set`

**Ressourcen-Budget:** Im Default-Profil zusätzliche ~210 MB RAM (Prom 80 MB + Grafana 110 MB + Exporter 20 MB).
**Geschätzte PR-Größe:** ~400 Lines diff
**Fertig wenn:** Compose-Default-Profil bringt Grafana auf `localhost:3000` (intern), `/metrics` antwortet mit Bearer.

---

### M0.10 — branch-and-pr-rules-md

**Branch:** `docs/branch-and-pr-rules-md`
**Issue:** `—`
**Vorbedingungen:** M0.7 gemerged (CI-Workflow steht, kann referenziert werden)
**Berührte Pfade:**

```
docs/operations/branch-and-pr-rules.md    ← Konsolidierung aller PR-/Branch-Regeln
CONTRIBUTING.md                            ← Verlinkt darauf
README.md                                  ← Verlinkt darauf
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `docs/operations/branch-and-pr-rules.md` enthält:
   - Branch-Naming (`feature/`, `fix/`, `refactor/`, `test/`, `docs/`, `chore/`)
   - Issue-Workflow (wann Issues, wann nicht — wie in `00-index.md` Sektion 2 definiert)
   - PR-Pflicht-Sektionen (`Summary`, `Acceptance criteria`, `Test plan`)
   - Commit-Subject-Form `(#NNN)`
   - Squash-Merge-Default
   - „Was tun, wenn der Cursor-Coauthor-Trailer doch reingerutscht ist"
   - Approved-Deletions-Verfahren (mit Beispiel-Commit)
2. `CONTRIBUTING.md` ist auf 1 Bildschirmseite reduziert: minimaler Onboarding-Text, dann Verweis.
3. `README.md` hat einen prominenten Hinweis-Block:
   > „**Vor dem ersten Commit:** Lies `docs/operations/branch-and-pr-rules.md`."

**Tests:**

- `tests/test_docs_links.py::test_contributing_links_present`
- `tests/test_docs_links.py::test_readme_pr_pointer_present`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~200 Lines diff
**Fertig wenn:** AC + CI grün.

---

## 5. Phasen-Gate

M0 gilt als grün abgeschlossen, wenn:

1. Alle Schritte M0.1 – M0.10 in `00-index.md` auf `[x]` stehen.
2. **Smoke** auf der echten Hub-VM:
   - `docker compose -f hub.yml --profile minimal up -d` läuft.
   - `https://terra.<example>.tld/v1/health` antwortet 200.
3. **Smoke** auf der echten Vault-VM:
   - `docker compose -f vault.yml --profile minimal up -d` läuft.
   - `https://mirror.app.terra.<example>.tld/` zeigt Statusseite.
4. **CI-Pipeline** ist grün auf einer leeren PR (zur Verifikation).
5. **`pre-commit`** läuft lokal in < 10 s auf einem unveränderten Commit.
6. **Dokumentations-Abschluss:** Pflichtbundle gemäß **`app/docs/greenfield/implementation/mvp/00-index.md`** §6 (insb. Nr. 7) und §7 „Am Abschluss einer ganzen Phase".
7. **Tag** `v0.1.0` ist gesetzt und gepusht.
8. **`catchup.md`** hat einen Eintrag „Greenfield M0 abgeschlossen".

---

## 6. Erledigte Änderungen

> Format: `[yyyy-mm-dd] M0.k slug — Kurz-Notiz (PR #NNN)`

- `[2026-05-09] M0.5 cloudflared-config-hub — Tunnel-YAML für Hub/Vault, Compose-Binds, Quicktunnel-Overrides; Lint-Test gegen Duplikat-Hostnames (PR #10).`
- `[2026-05-09] M0.6 pre-commit-baseline — Ruff/Prettier/Protected-Deletions + Cursor-Coauthor-Strip; Makefile bootstrap installiert Hooks (PR #10).`
- `[2026-05-09] M0.7 github-actions-ci-baseline — CI-Jobs (Lint, Mypy, Tests/Coverage, Schema, Protected-Deletions, Secrets-Layout, Pre-commit-CI, Compose-Smokes inkl. Observability); ergänzende Workflow-Stubs Build/CD/Nightly (PR #10).`
- `[2026-05-09] M0.8 secrets-sops-baseline — .sops.yaml, verschlüsseltes hub.sops.yaml, Dev-Age-Template, Ops-Doku + Ansible-Beispiel + Layout-Tests (PR #10).`
- `[2026-05-09] M0.9 logging-and-observability-baseline — Prometheus/Grafana im Hub-Default-Profil, API /metrics mit Bearer, Stub-Dashboards + Integration-Marker compose_observability (PR #10).`
- `[2026-05-09] M0.10 branch-and-pr-rules-md — docs/operations/branch-and-pr-rules.md, README/CONTRIBUTING-Verweise, Link-Tests (PR #10).`

---

_Stand: 2026-05-09 · Phase M0 Dokumentation und Repo-Artefakte geschlossen — Gate §5 (VM-Smokes, Tag-Push) wie dort beschrieben manuell erledigen._
