# `app/docs/greenfield/` — Greenfield-Plan für Terra Incognita

> **Lebendiges Dokument.** Dieser Ordner enthält den vollständigen Plan für den
> Greenfield-Neuaufbau des Drei-Pol-Systems (LNN ↔ EBM ↔ KG) — vom MVP auf
> Oracle-Always-Free-Hardware bis zum Vollausbau auf einer M4-Mac-Workstation.
>
> Diese Datei ist der **Einstiegspunkt**. Sie navigiert dich zu den richtigen
> Detail-Dokumenten — sie wiederholt deren Inhalte nicht.

**Persistenz (v1.0):** Der Hub nutzt **SQLite** (WAL + **FTS5** für Replay‑Suche) mit **Litestream → R2**, nicht DuckDB — siehe **`decisions/001-sqlite-litestream.md`** und **`architecture/mvp.md`**.

---

## Lesereihenfolge (für jede neue Person, jeden neuen Subagenten, jede neue Session)

1. **Diese Datei** (`README.md`) — Orientierung, Versionsfahrplan, Pfad-Kontext.
2. **`00-glossary.md`** — Begriffe, IDs, Abkürzungen. Was ist ein „Hub"? Was ist
   eine `F.*`-Formel-ID? Was ist ein „Encounter"?
3. **`architecture/truth-anchors-and-ghosts.md`** — zwei Truth Anchors (API/Seeds
   vs. Formeln), Seeds→Geist, dauerhaftes Speichern, Mehr‑DB‑Pfad, Automatisierung.
4. **`architecture/mvp.md`** — Architektur des MVP (v1.0 auf 2× AMD Micro mit
   Cloudflare Tunnel). **Lesepflicht** vor jeder Code-Arbeit am MVP.
5. **`architecture/production.md`** — Architektur des Vollausbaus (v2.0 auf
   M4-Mac). Lesepflicht, sobald die Hardware verfügbar ist und v1.x → v2.0
   geplant wird.
6. **`implementation/mvp/00-index.md`** — Phasen-Übersicht, Status-Tabelle,
   Akzeptanzkriterien, Branch-Mapping. Hier steht, **was als Nächstes kommt**.
7. **`implementation/mvp/M0..M8-*.md`** — die jeweils aktuelle Phasen-Datei,
   bevor an einem Branch dieser Phase gearbeitet wird.
8. **`formulas/README.md`** + **`formulas/registry.md`** — wenn Code eine Formel
   implementiert: erst die Registry-ID nachschlagen oder anlegen.
9. **`protocols/pdf-lookup.md`** — wenn eine PDF-Stelle gebraucht wird.

**Am Abschluss einer Phase `Mn`** (alle Steps dieser Phase in **`app/docs/greenfield/implementation/mvp/00-index.md`** auf `[x]`): Pflicht-Dokumentations-Bundle gemäß **`app/docs/greenfield/implementation/mvp/00-index.md`** §6–7 (Tag, `catchup.md`, Architektur-Spalte, README/CONTRIBUTING/CLAUDE vs CI/Makefile, Phasen-Gate, Memory).

---

## Versionsfahrplan auf einen Blick

| Tag        | Bedeutung                                                                | Auslöser                                |
|------------|--------------------------------------------------------------------------|------------------------------------------|
| `v0.1.0`   | Bootstrap done — Repo, CI, Compose lokal grün                            | M0 abgeschlossen                          |
| `v0.2.0`   | Datenfundament + Persistenz (SQLite + Litestream → Cloudflare R2)        | M1 abgeschlossen                          |
| `v0.3.0`   | Engine-Protokoll fixiert; Server akzeptiert lokale Engine-Sessions       | M2 abgeschlossen                          |
| `v0.4.0`   | Lokales Engine-Skelett läuft (LNN/EBM/KG-Stubs, kein echtes Lernen)      | M3 abgeschlossen                          |
| `v0.5.0`   | Erste echte Formel-Implementierung im LNN-State (`F.LNN.STATE.*`)        | M4 abgeschlossen                          |
| `v0.6.0`   | API-Surface komplett, Auth + Multi-User funktional, OpenAPI frozen       | M5 abgeschlossen                          |
| `v0.7.0`   | Frontend kann sich verbinden, Live-Stream sichtbar, 3D-Cockpit lädt      | M6 abgeschlossen                          |
| `v0.8.0`   | Replay & `/diagnostic` produktiv                                          | M7 abgeschlossen                          |
| `v0.9.0`   | Hardening (Cloudflare Tunnel-Härtung, Backups, OOM-Schutz, Multi-User)   | M8 in Arbeit                              |
| **`v1.0.0`** | **MVP — Public-Facing Schaufenster, multi-user, lokale Engine-Anbindung** | **M8 + Multi-User-Smoke-Test grün**        |
| `v1.x.y`   | Stabilisierung + neue Inhalte ohne Architekturwechsel                     | nach v1.0                                  |
| `v2.0.0`   | **Vollausbau auf M4** (Polyglot-Stack, alles serverseitig)               | M4-Hardware verfügbar + Stage-2 abgenommen |

`v0.x.y`-Patches innerhalb einer Phase, `v0.x.0`-Bumps zwischen Phasen.

---

## Hardware-Realität, die diesen Plan formt

**Aktuell verfügbar:** 2× Oracle Cloud `VM.Standard.E2.1.Micro` (AMD, ⅛ OCPU,
1 GB RAM pro VM) im Always-Free-Tier, plus Cloudflare-Free-Account mit Tunnel.

**Was das bedeutet:**

* Die volle LNN/EBM/KG-Engine **passt nicht** in 1 GB RAM (PyTorch alleine
  belegt ~400 MB Resident).
* Eine produktive PostgreSQL-Instanz mit den vier benötigten Extensions (AGE,
  pgvector, TimescaleDB, pg_trgm) läuft realistisch nicht auf 1 GB neben den
  übrigen Diensten.
* Die Antwort ist **kein** Sparbau auf VMs, sondern eine bewusste
  Topologie-Entscheidung: **Server = Schaufenster, Client = Hirn**.

**Konsequenz:** Die LNN/EBM/KG-Engine läuft im MVP **lokal auf der Workstation
des Nutzers** und spricht über eine authentifizierte WebSocket-Verbindung mit
dem Server. Der Server persistiert, verteilt und visualisiert; er rechnet
nicht. Beim Wechsel auf M4 wandert die Engine in den Server (siehe
`architecture/production.md`); die Schnittstelle bleibt unverändert.

**Wichtig:** Diese Topologie ist nicht zweite Wahl, sondern eine saubere
Trennung von Compute und Surface, die auch im Vollausbau bestehen bleibt.
Ein Nutzer auf M4 wird im Server selbst rechnen lassen — ein Power-User mit
Heim-GPU kann die Engine bei sich behalten, das Protokoll ist identisch.

---

## Pfad-Kontext (was ist „Pfad B"?)

Während der Architektur-Verhandlung wurden drei Pfade evaluiert:

| Pfad | Hardware                                | Scope                                                                 |
|------|-----------------------------------------|-----------------------------------------------------------------------|
| A    | 2× ARM A1 (12 GB / 2 OCPU)              | Voller MVP mit Engine auf VM (verworfen — keine ARM-Kapazität)        |
| **B** | **2× AMD Micro (1 GB / ⅛ OCPU)** + CF Tunnel | **Thin-Shell-MVP — dieser Plan** |
| C    | AMD Micro + Oracle Autonomous DB        | Hybrid (verworfen — Autonomous DB ist nicht Postgres-mit-Extensions)  |

**Dieser Plan implementiert Pfad B.** Falls sich ARM-Kapazität später
befreit, wechselt der Plan **nicht automatisch** auf Pfad A. Stattdessen ist
ein Hardware-Upgrade ein eigener Migrations-Schritt zwischen v1.x und v2.0,
weil v2.0 ohnehin auf M4 zielt.

---

## Verzeichnis-Layout

```
app/docs/greenfield/
├── README.md                       ← diese Datei
├── CHANGELOG.md                    ← Greenfield-Plan-Versionsspur
├── 00-glossary.md                  ← Begriffe + IDs
│
├── architecture/
│   ├── mvp.md                      ← v1.0 Thin-Shell auf 2× AMD Micro (detailliert)
│   ├── truth-anchors-and-ghosts.md ← Seeds→Geist, Truth Anchors, API-Growth
│   ├── production.md               ← v2.0 Polyglot auf M4 (mittlere Tiefe)
│   ├── data-model.md               ← Kanonisches Datenmodell v1.0 → v2.0
│   ├── security.md                 ← Threat-Modell, Kontrollen, Tests
│   ├── observability.md            ← Metriken, Logs, Traces, SLOs, Alerts
│   └── frontend.md                 ← React/R3F-Stack, Pages, Performance-Vertrag
│
├── implementation/
│   ├── mvp/                        ← v1.0 Phasen, hochdetailliert, mit Branches
│   │   ├── 00-index.md             ← Phasen-Übersicht, Status-Tabelle, Branch-Mapping
│   │   ├── M0-bootstrap.md
│   │   ├── M1-data-foundation.md
│   │   ├── M2-engine-protocol.md
│   │   ├── M3-local-engine-skeleton.md
│   │   ├── M4-first-formula-lnn-state.md
│   │   ├── M5-api-surface.md
│   │   ├── M6-frontend-bootstrap.md
│   │   ├── M7-replay-diagnostics.md
│   │   └── M8-hardening-deploy.md
│   └── production.md               ← v2.0 Was/Wann + Phasen P0–P5
│
├── formulas/
│   ├── README.md                   ← Registry-Konvention, ID-Schema, Workflow
│   ├── registry.md                 ← `F.*`-Formel-Einträge
│   └── derivations.md              ← Schritt-für-Schritt-Herleitungen
│
├── protocols/
│   ├── pdf-lookup.md               ← Menschenlesbarer Lookup-Vertrag
│   ├── replay-contract.md          ← `replay_timeline_window_v4` (frozen)
│   ├── snapshot.md                 ← Engine-Snapshot-Protokoll
│   ├── event-log.md                ← NATS v1.0 → Redpanda v2.0
│   └── auth-flow.md                ← Login/Refresh/Logout/Engine-Auth
│
├── runbooks/
│   ├── disaster-recovery.md        ← DR-Szenarien A–G + Drill-Plan
│   ├── oom-and-capacity.md         ← OOM-Schutz, cgroups, Soak-Tests
│   ├── operations.md               ← Tag/Woche/Monat-Routinen, Eingriffe
│   ├── cloudflare-tunnel.md        ← Tunnel-Config, WAF, mTLS, Token-Rotation
│   └── local-engine-onboarding.md  ← Engine installieren, enrollen, betreiben
│
├── decisions/
│   ├── README.md                   ← ADR-Index
│   ├── 000-baseline.md
│   ├── 001-sqlite-litestream.md
│   ├── 002-nats-jetstream.md
│   ├── 003-engine-mtls.md
│   ├── 004-replay-hybrid-frozen.md
│   ├── 005-snapshot-format.md
│   ├── 006-formula-id-schema.md
│   ├── 007-pdf-lookup-protocol.md
│   ├── 008-polyglot-stack-v2.md
│   ├── 009-argon2id.md
│   ├── 010-rs256-jwt.md
│   ├── 011-cookie-strategy.md
│   ├── 012-k3s-cluster.md
│   └── 013-engine-pool-topology.md
│
└── contracts/
    └── openapi-v1-summary.md       ← OpenAPI v1 (Lese-Zusammenfassung)
```

Korrespondierende Datei für Subagenten: `.cursor/agents/pdf-lookup-protocol.md`
(gleicher Vertrag im Agent-Profil-Format).

> Eine maschinen­lesbare OpenAPI-Datei (`docs/contracts/openapi/v1.json`)
> wird in M5.14 erzeugt und gilt parallel zum Lese-Summary.

---

## Was außerhalb dieses Ordners NICHT angefasst wird

Greenfield heißt nicht „alles wegwerfen". Folgende bestehende Artefakte sind
**Quellen**, die in den Greenfield-Plan einfließen, aber nicht ersetzt werden:

| Bestehend                                                | Bleibt — wofür                                                              |
|----------------------------------------------------------|------------------------------------------------------------------------------|
| `Anweisungen.md`                                         | Übergeordnetes Regelwerk; Greenfield-Pläne respektieren §1–§10 unverändert. |
| `CLAUDE.md`                                              | Orchestrator-Referenz; verlinkt diese Greenfield-Dokumente mit.              |
| `catchup.md`                                             | Session-Log; Greenfield-Sessions tragen sich hier wie alle anderen ein.      |
| `archive/legacy-docs/Implementierungen.Architektur.md`                       | Gesamtstatus; bekommt eine zusätzliche Spalte für „Greenfield-Ziel-State".   |
| `docs/ARCHITECTURE.md`                                   | Architektur des **bestehenden** Systems; bleibt Referenz.                    |
| `docs/PRODUCT_REPLAY_AND_TIMELINE.md` und Verwandte      | Produkt-/Replay-Anforderungen; Greenfield erbt diese Anforderungen.          |
| `research/extracted/*` (64 Papers, L0–L4, l4_formulas)   | Quellmaterial für `formulas/registry.md`; nichts wird verändert.             |
| `.cursor/agents/*.md`                                    | Agent-Profile; das neue `pdf-lookup-protocol.md` reiht sich ein.             |
| `.cursor/rules/*.mdc`                                    | Cursor-Regeln (PR-Workflow, NO-SILENT-DELETIONS, …); strikt befolgt.         |

---

## Dieser Plan und die `Anweisungen.md`-Regeln

Alle Greenfield-Dokumente sind **Living Documents** im Sinne von
`Anweisungen.md` §8. Erweitern, anpassen, überschreiben ist erlaubt — per
Commit dokumentiert, mit Begründung.

Verbindliche Regeln, die der Plan respektiert:

* **Python 3.12, async/await, type hints, dataclasses** (§2)
* **Implementierung.{name}.md** für jedes Modul (§3) — Greenfield-Module
  bekommen Implementierungs-Docs, sobald sie tatsächlich codiert werden
* **Kein Code ohne Tests** (§4) — jede Phase hat Test-Akzeptanzkriterien
* **Commit-Format `(#NNN)`** (§5) — siehe `implementation/mvp/00-index.md`
  zur Branch-/PR-Konvention
* **Non-Negotiables LNN/EBM/Tiers** (§7) — der Plan baut sie nicht um, er
  baut sie **diszipliniert auf**

---

## Wie dieser Plan wächst

* **Pro abgeschlossener Phase Mn** wird `00-index.md` aktualisiert (Status
  von `[ ]` auf `[x]`, PR-Nummer, Datum), und die Phasendatei `Mn-*.md`
  bekommt einen Eintrag „Erledigte Änderungen".
* **Pro neuer `F.*`-Formel** kommt ein Eintrag in `formulas/registry.md` mit
  PDF-Verweis und Konsumenten.
* **Pro Architektur-Abweichung** wird die jeweilige `architecture/*.md`-Datei
  mit Datum + Begründung ergänzt.

Diese Datei (`README.md`) wird selten geändert — nur bei Versionsmeilensteinen
oder wenn sich der Pfad fundamental verändert.

---

## Nächste Schritte für jeden Leser

* **Du kommst neu rein:** lies `00-glossary.md`, dann
  `architecture/truth-anchors-and-ghosts.md`, dann `architecture/mvp.md`.
* **Du willst implementieren:** lies die nächste offene Mn-Datei in
  `implementation/mvp/`, prüfe Akzeptanzkriterien, eröffne den passenden
  Branch.
* **Du willst eine Formel implementieren:** lies `formulas/README.md`,
  schlage die ID nach oder lege eine an, dann implementiere.
* **Du willst die Forschung referenzieren:** lies `protocols/pdf-lookup.md`
  und befrage das Lookup-Protokoll.
* **Du planst v2.0:** lies `architecture/production.md` und
  `implementation/production.md`.
* **Du brauchst eine Architektur-Entscheidung im Kontext:** schau in
  `decisions/` (ADR-Index unter `decisions/README.md`).
* **Du operierst (Inzident, DR-Drill, OOM-Stress):** schau in
  `runbooks/`.
* **Du implementierst eine Auth- oder Replay-Route:** lies vorab
  `protocols/auth-flow.md` bzw. `protocols/replay-contract.md`.
* **Du brauchst die OpenAPI-Übersicht:** lies
  `contracts/openapi-v1-summary.md` (lesen­freundliche Spiegelung der in
  M5.14 zu erzeugenden `docs/contracts/openapi/v1.json`).

---

## Wo stehen welche Inhalte? (Schnell-Index)

| Frage                                          | Datei                                                        |
|------------------------------------------------|--------------------------------------------------------------|
| Seeds→Geist, Truth Anchors, API dauerhaft speichern? | `architecture/truth-anchors-and-ghosts.md` |
| Was ist ein Encounter / Hub / Vault?           | `00-glossary.md`                                              |
| Wie sind Memory-Budgets pro Service?           | `architecture/mvp.md` §Memory-Budgets · `runbooks/oom-and-capacity.md` §1 |
| Was ist das SQLite-Schema?                     | `architecture/data-model.md` §3                               |
| Was ist das Polyglot-Mapping v1→v2?            | `architecture/data-model.md` §7                               |
| Wie sind Authentifizierung und Cookies?        | `protocols/auth-flow.md` · `architecture/security.md` §3      |
| Wie funktioniert Replay-Hybrid-Ranking?        | `protocols/replay-contract.md` · `formulas/registry.md F.REPLAY.HYBRID.001` |
| Wie sind Snapshots aufgebaut?                  | `protocols/snapshot.md` · `architecture/data-model.md` §6     |
| Welche Events laufen über NATS?                | `protocols/event-log.md` §2 + §3                              |
| Welche Metric-IDs gibt es?                     | `architecture/observability.md` §3                            |
| Welche Alerts feuern wann?                     | `architecture/observability.md` §7                            |
| Was passiert bei Hub-Disk-Loss?                 | `runbooks/disaster-recovery.md` §3                            |
| Welche Formeln sind implementiert?              | `formulas/registry.md`                                        |
| Wie wird eine Formel hergeleitet?               | `formulas/derivations.md`                                     |
| Welche Architektur-Entscheidungen gelten?       | `decisions/README.md` (Index)                                 |
| Wie ist OpenAPI v1 strukturiert?                | `contracts/openapi-v1-summary.md`                             |

---

*Stand: 2026-05-09 · unter `app/docs/greenfield/` · Pfad B (Thin-Shell auf 2× AMD Micro)*
