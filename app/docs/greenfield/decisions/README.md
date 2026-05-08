# `decisions/` — Greenfield Architecture Decision Records

> **Zweck.** Lebendiger ADR-Index für den Greenfield-Plan. Jede
> nicht-triviale Architektur-/Vertrags­entscheidung erhält einen
> eigenen ADR. Format orientiert sich am etablierten ADR-Standard
> (Status / Context / Decision / Consequences / Alternatives).

---

## Status-Werte

* **Proposed** — Diskussionsstand, kein Code-Effekt.
* **Accepted** — gilt; Code/Doku müssen konsistent sein.
* **Superseded** — durch späteren ADR ersetzt; Verweis auf Nachfolger.
* **Deprecated** — gilt nicht mehr; kein Nachfolger nötig.

---

## Index

| ID    | Titel                                                                  | Status   |
|-------|-------------------------------------------------------------------------|----------|
| ADR-000 | Baseline & Lock-In: Greenfield-Plan, Pfad B (Thin-Shell auf 2× AMD Micro) | Accepted |
| ADR-001 | SQLite + Litestream als v1.0-Persistenz                                  | Accepted |
| ADR-002 | NATS JetStream als v1.0-Event-Spine                                       | Accepted |
| ADR-003 | mTLS für Engine-Hub-Verbindung                                            | Accepted |
| ADR-004 | Replay-Hybrid-Score (`F.REPLAY.HYBRID.001`) eingefroren                   | Accepted |
| ADR-005 | Snapshot-Format `tar.zst` mit `manifest.json`-First                       | Accepted |
| ADR-006 | `F.{POL}.{TOPIC}.{NNN}`-Formel-ID-Schema                                  | Accepted |
| ADR-007 | PDF-Lookup-Protokoll als Pseudo-Subagent                                  | Accepted |
| ADR-008 | Polyglot-Stack-Auswahl (Neo4j/Qdrant/ClickHouse/Postgres/OpenSearch/Redpanda/Dragonfly/MinIO) | Accepted (für v2.0) |
| ADR-009 | Argon2id für Passwort-Hashing in v1.0                                     | Accepted |
| ADR-010 | RS256-JWT mit `kid`-Rotation                                              | Accepted |
| ADR-011 | Cookie-Strategie (`HttpOnly`, `SameSite=Strict`, `Secure`)                 | Accepted |
| ADR-012 | k3s als v2.0-Cluster-Substrat                                             | Proposed |
| ADR-013 | Engine-Pool-Topologie (1 Prozess pro Tenant, idle-suspend)                | Proposed |

---

## Wie wird ein neuer ADR angelegt?

1. Neue Datei `decisions/NNN-kebab-titel.md`, `NNN` monoton steigend.
2. Vorlage:

   ```markdown
   # ADR-NNN — <Titel>

   * **Status:** Proposed
   * **Datum:** YYYY-MM-DD
   * **Bezug:** <PR-#>, <Issue-#>, <Doku-Verweis>

   ## Context

   <Was ist die Frage / das Problem?>

   ## Decision

   <Was wurde entschieden?>

   ## Consequences

   <Welche Auswirkungen hat das?>

   ## Alternatives Considered

   <Welche Alternativen wurden geprüft, warum verworfen?>

   ## References

   <Links zu Doku / PDF / Tests>
   ```
3. Index in `decisions/README.md` aktualisieren.
4. Bei `Accepted` muss in `memory/system/decisions.md` ein
   Spiegel-Eintrag mit Datum entstehen (Pflicht laut
   `Anweisungen.md` §7).

---

*Stand: 2026-05-08 · Greenfield-Initial.*
