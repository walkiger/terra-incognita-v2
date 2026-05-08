# Glossar — Greenfield-Plan

> Begriffe, IDs, Abkürzungen. Wer in dieser Doku ein Wort nicht versteht,
> findet es hier — oder fügt es hinzu.

Sortierung: **konzeptuelle Cluster zuerst**, alphabetisch innerhalb des
Clusters.

---

## 1. Drei-Pol-System (Kernarchitektur)

### LNN — Liquid Neural Network
Stateful, zeit-kontinuierliches neuronales Netz mit verstecktem Zustand `h`.
Im Greenfield basiert es auf der **Closed-Form-Cell-Variante (CfC)** aus
Hasani et al. 2022 (siehe `formulas/registry.md` → `F.LNN.*`).

* **`iD`** — Input-Dimension. Wächst mit Tier-Emergenz (`B`, `B+B`, `B+2B`, …).
* **`hD`** — Hidden-Dimension. Identisch zu `iD` (**Invariante: `hD = iD`**).
* **`B`** — Basis-Einheit, default `256`. Konfigurierbar in `settings.py`.
* **Wachstumsformel:** `dim(N) = B × (1 + N×(N+1)/2)`. Siehe `Anweisungen.md` §7.
* **`lnn_step(word, scale, state)`** — einziger Einstiegspunkt für
  LNN-Stimulation. Niemals `lnn.step()` direkt aufrufen. Begründung:
  `archive/legacy-docs/Implementierung.backend.core.lnn.md`.
* **`build_lnn_input()`** — baut Multi-Tier-Vektor; nie direkter `wv()`-Call.
* **`_on_tier_stable(tier_n)`** — einziger Ort, an dem `lnn.grow()` feuert.
* **T0** — startet die LNN-Geburt (Dimension = `B`), aber **wächst sie nicht**.

### EBM — Energy-Based Model
Hopfield-artiges Energie-Landschafts-Modell über KG-Knoten. Findet stabile
Energieminima → Wells → Attraktoren → Tier-Hierarchie.

* **`ebm.wells`** — registrierte Energie-Minima. **Invariante:** niemals
  `.pop()` / `.clear()` / `del` — nur `make_dormant()`.
* **`ebm_tick()`** — pro `ebm_tick_cadence`-System-Ticks aufgerufen.
* **`hopfield_energy()`** — Energie-Funktion (siehe `formulas/registry.md` →
  `F.EBM.ENERGY.*`).
* **`adapt_ebm_theta()`** — adaptiver Schwellenwert.
* **`find_energy_wells()`** — **einzige und universelle** Tier-Detection-
  Funktion. Sie deckt T0 → TN ab; keine separaten Funktionen pro Tier
  (`Anweisungen.md` §7).

### KG — Knowledge Graph
Semantisches Substrat. Knoten = Konzepte, Kanten = typisierte Relationen.

* **`KG_NODES`** — Konzept-Tabelle (im Greenfield: SQLite-Tabelle `kg_nodes`).
* **`KG_EDGES`** — Relation-Tabelle (`kg_edges`), getypt nach Relation-Vokabular
  in `docs/RELATIONS.md`.
* **Hebbian Write-Back** — `lnn_to_kg_hebbian()` schreibt LNN-Aufmerksamkeit
  zurück in Kantengewichte (`F.KG.HEBBIAN.*`).
* **Spontaneous Propagation** — `kg_spontaneous_prop()` feuert ohne externen
  Reiz aktive Knoten weiter (`F.KG.SPREAD.*`).
* **Synaptic Pruning** — `synaptic_prune()` entfernt schwache Kanten.

### Encounter
Der **einzige Weg**, wie das System neues Wissen aufnimmt. Kein Konzept ohne
Encounter — Provenance ist heilig (`Anweisungen.md` §1).

* **Encounter-Strom** — chronologische Sequenz aller Encounter eines Nutzers.
* **Encounter-Event** — strukturierte Repräsentation eines einzelnen Vorgangs
  (Wort + Skalierung + Kontext + Zeit).
* **Encounter → Tier** — Encounter erzeugt Aktivität → EBM findet Wells →
  Tier-Emergenz → LNN wächst.

### Tier-Hierarchie
Emergente Schicht-Struktur, die aus EBM-Wells kristallisiert.

| Tier | Bedeutung      | LNN-Effekt              |
|------|-----------------|--------------------------|
| T0   | Attraktor       | LNN-Geburt (`iD = B`)    |
| T1   | Well            | LNN wächst auf `2B`       |
| T2   | Konzept         | LNN wächst auf `3B`       |
| T3   | Framework       | LNN wächst auf `4B`       |
| T4+  | offen-endig     | weiterer LNN-Wachstum     |

---

## 2. Greenfield-Topologie (Pfad B, MVP)

### Hub
**VM-A** im Oracle-Cluster. Aktiver, internetzugewandter Knoten. Trägt
FastAPI, NATS-leichten-Broker, SQLite-Primary, Cloudflared-Tunnel, Caddy.

### Vault
**VM-B** im Oracle-Cluster. Stiller Sicherungsknoten. Trägt SQLite-Replica
(aus R2 wieder eingespielt), zweiten Cloudflared-Tunnel als Failover, Backup-
Automation, statische Frontend-Auslieferung.

### Local Engine
Python-Prozess auf der Workstation des Nutzers. Trägt LNN/EBM/KG mit
PyTorch/NumPy. Verbindet sich über authentifizierte WebSocket-Verbindung mit
dem Hub. **Hier passiert die eigentliche Berechnung.**

### Frontend
React-/R3F-Single-Page-App. Wird von Caddy auf Hub oder Vault statisch
ausgeliefert; verbindet sich vom Browser des Nutzers mit dem Hub-API.

### Tunnel
**Cloudflare Free Tunnel** (`cloudflared`). Public-Hostname → VM, ohne offene
Inbound-Ports. Bereits eingerichtet (Stand 2026-05-08).

### R2
**Cloudflare R2** — S3-kompatibler Object-Store. 10 GB Always-Free, **kein
Egress-Cent**. Trägt im MVP: Litestream-Backups der Hub-SQLite, Replay-
Snapshot-Bundles, optional PDF-Forschungs-Mirror.

### Litestream
Tool, das SQLite-WAL kontinuierlich nach S3/R2 streamt. Erlaubt Disaster-
Recovery in Minuten ohne ein zweites laufendes DB-Server-Pendant.

---

## 3. Greenfield-Topologie (Vollausbau, v2.0)

### M4-Hub
M4-Mac (192 GB RAM Ziel) als zentraler Compute- und Persistenz-Knoten.
Trägt im Vollausbau: FastAPI, Tick-Engine in eigenem Prozess, alle
Polyglot-Stores, Projektoren.

### Polyglot-Stack
Sammelbegriff für die nicht-konsolidierte Datenhaltung in v2.0:

| Engine        | Rolle                                       |
|---------------|---------------------------------------------|
| Neo4j         | Knowledge Graph (Tier-Detection via GDS)     |
| Qdrant        | Vektorraum (Embeddings, Similarity)          |
| ClickHouse    | Tick-/Replay-Analytik                        |
| PostgreSQL    | Operativer Zustand, Sessions, Konfig         |
| OpenSearch    | Volltextsuche                                |
| MinIO         | Objekt-Storage                               |
| Redpanda      | Event-Log-Spine (Kafka-API)                  |
| DragonflyDB   | Cache + Pub/Sub                              |

### Event-Log-Spine
Architektur-Prinzip: alle Schreibwege gehen erst in das Event-Log
(MVP: NATS JetStream; Vollausbau: Redpanda). Die Datenbanken sind
**Projektionen** dieses Logs. Replay = „Log zurückspulen, neu projizieren".

---

## 4. Sicherheit & Identität

### JWT
JSON Web Token. Authentifizierung am Hub für API + WebSocket. RS256-signiert,
Schlüssel in Hub-Secrets.

### Cloudflare Access (optional)
Zero-Trust-Layer vor dem Tunnel. Im MVP nur für Admin-Routen aktiviert
(`/admin/*`), nicht für normale Nutzer-Sessions.

### mTLS (Engine-WS)
Lokale Engine authentifiziert sich am Hub-WS zusätzlich mit
Client-Zertifikat — schützt vor gestohlenem Token, der zum Engine-Spoofing
genutzt würde.

### Tenant
Im MVP synonym mit „Nutzer-Account". Multi-Tenant heißt: **mehrere parallele
Sessions verschiedener Nutzer**, jeder mit isoliertem Encounter-Strom.

---

## 5. Datenmodell-Begriffe

### Snapshot
Vollständiger Serialisierungs-Stand des Drei-Pol-Systems zu einem Zeitpunkt.
Enthält LNN-Gewichte, EBM-Wells, KG-Knoten/Kanten, Tier-Registry. Format:
versioniertes JSON oder Protobuf-Bundle, gepackt als `.tar.zst`.

### Replay-Event
Atomares Event in der Wiedergabe-Zeitachse. Felder:
`(id, ts, kind, payload, schema_version)`. Speicherort: SQLite-Tabelle
`replay_events` (MVP); ClickHouse (v2.0).

### Replay-Window
Server-seitig konfigurierbare Sicht auf eine Sub-Sequenz des Replay-Stroms.
Aktueller Contract: `replay_timeline_window_v4` (siehe
`docs/contracts/replay_timeline_window_v4.schema.json`). Greenfield erbt das.

### Preseed
Initial-Wissen, das das System beim ersten Boot kennt. Im Greenfield aus
`knowledge/preseed_v2.json` übernommen, **nicht neu erstellt**.

### Wave
Tranchierte Preseed-Schicht (`w00`–`w12`). Ermöglicht graduelle KG-Ladung.

---

## 6. Identitäten und IDs

### `F.{POL}.{TOPIC}.{NNN}` — Formel-ID

Stabile, sortierbare ID einer Formel im Formula-Registry.

* `POL` ∈ `{LNN, EBM, KG, PRESEED, INFER, REPLAY, …}`
* `TOPIC` — sprechender Bezeichner (z. B. `STATE`, `GROW`, `ENERGY`, `WELL`,
  `HEBBIAN`, `SPREAD`, `TIER`, `RELATION`)
* `NNN` — laufende Nummer mit führenden Nullen (3 Stellen)

Beispiele:
* `F.LNN.STATE.001` — CfC Hidden-State-Update
* `F.LNN.GROW.003` — Tier-Emergenz-Schwelle
* `F.EBM.ENERGY.001` — Hopfield-Energie-Funktion
* `F.KG.TIER.005` — Universelle Tier-Detection

### `M{phase}.{step}` — MVP-Phase-Schritt

Identifiziert einen einzelnen geplanten Arbeits-Schritt im MVP-
Implementierungsplan. **Nicht** Teil des Branchnamens; lediglich
Plan-interne Referenz.

* Phasen: `M0`..`M8` (siehe `implementation/mvp/00-index.md`)
* Schritte: `.1`..`.N`, fortlaufend pro Phase

Beispiele:
* `M2.3` — „Producer-/Consumer-Wrapper für NATS"
* `M5.7` — „Auth-Middleware mit JWT-RS256"

### `(#NNN)` — GitHub-PR-Nummer

Pflicht-Suffix in der Subject-Zeile jedes Commits einer PR-tragenden Branch.
`Anweisungen.md` §5. Beispiel: `feat: nats jetstream broker (#42)`.

### `terra-XXX` — Session-Tag

Optionaler zusätzlicher Marker im Commit-Body oder Pull-Request-Beschreibung.
Bezieht sich auf eine Session in `catchup.md`. Greenfield-Sessions vergeben
keinen neuen `terra-XXX`-Range; sie nutzen den bestehenden Zähler weiter.

### `document_id` (Forschung)

Stabiler Identifier eines extrahierten PDFs in `research/extracted/`.
Beispiel:
`were_rnns_all_we_needed_leo_feng_mila_universit_e_de_montr_eal_borealis_20260508T150735Z`.
Schema in `research/schema/manifest.schema.json`.

### `eq_pageX_Y` (Forschung)

Lokale ID einer extrahierten Formel innerhalb eines Papers
(`l4_formulas.json`). Wird beim Lookup zusammen mit `document_id` zur global
eindeutigen Referenz.

---

## 7. Tooling & Infrastruktur

### Cloudflared
Cloudflare-Tunnel-Client. Daemon, der eine ausgehende QUIC/TLS-Verbindung
zur Cloudflare-Edge öffnet und Public-Hostnames an interne Services routet.
Kein offener Inbound-Port auf der VM nötig.

### Caddy
Single-Binary-Webserver, einfacher als Nginx, automatisches TLS, einfache
Reverse-Proxy-Config. Im MVP für statisches Frontend + lokale Reverse-Proxy
auf FastAPI.

### NATS JetStream
Leichter Message-Broker mit persistierten Streams. Single-Binary,
~50–80 MB RSS. Im MVP als Event-Log-Spine zwischen API, lokaler Engine
und Projektoren-Workern.

### SQLite (mit WAL)
Embedded-DB, `journal_mode=WAL`. Im MVP einzige Persistenz neben Object
Storage. Starke Read-Concurrency, einzelner Writer (für unseren Workload
mehr als ausreichend).

### Litestream
Streaming-Backup für SQLite. WAL-Frames kontinuierlich nach S3/R2 → Restore
in Minuten.

### Cloudflare R2
S3-kompatibler Object-Store. 10 GB im Free-Tier, **kein Egress-Cent**.

### Pre-commit
Tool für lokale Git-Hooks (`pre-commit-hooks`-Bibliothek). Im Repo bereits
konfiguriert, ergänzt um Greenfield-spezifische Hooks (siehe
`implementation/mvp/M0-bootstrap.md`).

### Docker / Docker Compose
Standard-Container-Runtime. Im MVP: `docker compose` mit Profilen
(`hub`, `vault`, `local-engine-dev`).

---

## 8. Begriffe aus dem Forschungs-Korpus

### L0 / L1 / L2 / L3 / L4
Extraktions-Schichten der PDF-Pipeline (siehe `research/README.md`):

| Schicht | Inhalt                                                                            |
|---------|-----------------------------------------------------------------------------------|
| L0      | Document-Identity + Bookkeeping (manifest.json)                                  |
| L1      | Roher Textauszug (`l1_raw_text.json`)                                              |
| L2      | Strukturierter Outline (`l2_outline.json`)                                         |
| L3      | Strukturierte Entitäten (`l3_entities.json`)                                       |
| L4      | Tiefenanalyse (Claims, Methods, Limitations) (`l4_analysis.json`)                  |
| L4-Formeln | Sidecar `l4_formulas.json` mit LaTeX-Bestform, Seitenzahlen, Verbatim-Snippets |

### `confidence` (Formel)
`high` / `medium` / `low`. Bei `low` ist die Extraktion textlich fragmentiert
(z. B. wegen PDF-Text-Layer). Wir verlassen uns dann zusätzlich auf
`evidence.verbatim_snippet` und das umgebende `l4_analysis.json`.

### Lookup-Pfad
Eine der drei Routen für PDF-Recherche-Anfragen, wie in
`protocols/pdf-lookup.md` definiert:

| Pfad | Mechanik                                | Wann                                     |
|------|------------------------------------------|------------------------------------------|
| 1    | Inline-Lookup über `Grep`/`Read`         | Kleine, exakte Anfragen                  |
| 2    | `Task(subagent_type="explore", …)`       | Multi-File-Synthese, read-only           |
| 3    | `Task(subagent_type="research-agent", …)` | Echte Neuextraktion eines neuen Papers   |

---

## 9. Compliance & Governance-Begriffe

### NO-SILENT-DELETIONS
Cursor-Regel `.cursor/rules/NO-SILENT-DELETIONS.mdc`. Verbietet das stille
Löschen geschützter Pfade (`docs/**`, `memory/**`, `tests/**`, …) ohne
explizite Klassifikation.

### Approved-Removal
Eine der vier Klassifikationen für Löschungen geschützter Pfade. Nur diese
erlaubt eine Löschung; benötigt einen Approval-Eintrag im Commit-Body
(`approved_deletions: <pfad>`) oder im PR-Spec.

### `meta` / `orch`
Zwei der Governance-Subagenten:
* **`meta`** — Genehmigungs-Gate, ALLOW/GUARDED/BLOCKED-Verdikte.
* **`orch`** — Planungs- und Delegierungs-Subagent für ganze Lifecycles.

Beide werden im MVP-Plan als sekundäre Reviewer angesprochen, nicht als
Treiber — der Treiber ist der Plan.

---

## 10. Kurz-Abkürzungs-Liste

| Abk. | Auflösung                                  |
|------|---------------------------------------------|
| AEAD | Authenticated Encryption with Associated Data |
| CfC  | Closed-Form Continuous-Time Cell (LNN)      |
| CSP  | Content Security Policy                     |
| DEK  | Data Encryption Key                         |
| DR   | Disaster Recovery                           |
| EBM  | Energy-Based Model                          |
| FT   | Full-Text (Search), z. B. SQLite-FTS5       |
| GDS  | Graph Data Science (Neo4j-Bibliothek)       |
| HA   | High Availability                           |
| HMAC | Hash-based Message Authentication Code      |
| INP  | Interaction to Next Paint (Web Vital)       |
| KEK  | Key Encryption Key                          |
| KG   | Knowledge Graph                             |
| LCP  | Largest Contentful Paint (Web Vital)        |
| LNN  | Liquid Neural Network                       |
| MFA  | Multi-Factor Authentication                 |
| MVP  | Minimum Viable Product                      |
| ODE  | Ordinary Differential Equation              |
| OOM  | Out-of-Memory (Linux-Kernel-Killer)         |
| OTP  | One-Time Password                           |
| OTel | OpenTelemetry                               |
| PR   | Pull Request                                |
| RPO  | Recovery Point Objective                     |
| RSS  | Resident Set Size                           |
| RTO  | Recovery Time Objective                      |
| SBOM | Software Bill of Materials                  |
| SCRAM| Salted Challenge Response Authentication M. |
| SLO  | Service Level Objective                     |
| SOPS | Mozilla SOPS (Secrets-Tool, age-Empfänger)   |
| SoT  | Source of Truth                             |
| SSE  | Server-Sent Events                          |
| TLS  | Transport Layer Security                    |
| TOTP | Time-based One-Time Password                |
| TZD  | Time-Zero Drift (interne Bezeichnung)       |
| WAL  | Write-Ahead Log (SQLite)                    |
| WAF  | Web Application Firewall                    |
| WS   | WebSocket                                   |
| WSS  | WebSocket Secure (TLS)                      |

---

## 11. Erweiterte v2.0-Begriffe (Stack-Detail)

### Neo4j Multi-DB
Neo4j 5 erlaubt mehrere logische Datenbanken in einem Cluster. Im
v2.0-Plan zunächst Single-DB mit `tenant_id`-Label-Filter; Multi-DB
ist optional ab v2.5.

### Qdrant Hybrid Search
Vektor-Score plus Payload-Filter, in einem Statement abgesetzt.
Genutzt für „top-50 Embeddings im Tier `n` und Sprache `de`".

### ClickHouse ReplacingMergeTree
Engine-Variante, die spätere Updates desselben Sort-Keys ersetzt.
Im v2.0-Plan für `replay_events_v2` verwendet, damit Korrekturen
ohne Tombstone möglich sind.

### Redpanda Tiered Storage
Optionales Feature, bei dem ältere Segmente nach S3 (oder MinIO)
ausgelagert werden. In v2.0 nicht initial nötig (1 Monat Retention
auf NVMe), aber Zukunfts-Pfad bei Wachstum.

### DragonflyDB Multi-Threaded
Im Gegensatz zu Redis (Single-Thread) skaliert Dragonfly horizontal
über Cores. Für Quota-Counter wichtig, weil Token-Bucket-Operationen
sehr viele Lese-/Schreib-Operationen erzeugen.

### MinIO Object-Lock
WORM-Modus (Write Once Read Many). Im v2.0-Plan für `audit/`
verpflichtend (5-Jahres-Retention, kein Override).

### k3s vs. Full-K8s
k3s ist ein Single-Binary-Distro mit eingebauter SQLite (oder
Etcd-Option). Full-K8s (`kubeadm`) hat höhere Operations-Last, ist
für 1–2 Node nicht angemessen.

### MPS (Apple Silicon)
Metal Performance Shaders — Apple-GPU-Backend für PyTorch. Auf M4
ersetzt es CUDA und liefert vergleichbare Geschwindigkeit für unsere
Modellgrößen (≤ 4096 Hidden-Dim).

### PEP 703
Python-Verbesserungs-Vorschlag für „free-threaded Python" (kein GIL).
Ab Python 3.13 als experimentelle Build-Variante; ab 3.14 stabil
erwartet. Für Engine-Pool-Topologie relevant (siehe
`decisions/013-engine-pool-topology.md`).

---

## 12. Greenfield-Plan-Begriffe

### Pfad B
Operativer Lock-In: Thin-Shell-MVP auf 2× AMD-Micro
(siehe `decisions/000-baseline.md`).

### Schaufenster
Nicht-Compute-VM-Rolle: serviert nur API, persistiert, koordiniert.
Engine-Compute liegt beim User.

### Engine-Pool
Server-seitige Lifecycle-Topologie für v2.0: ein Python-Prozess
pro aktivem Tenant, idle-suspend-fähig.

### `F.*`-Workflow
Lebenszyklus eines Formel-Eintrags: `spec-ready → implemented →
verified → superseded/retracted` (siehe `formulas/README.md`).

### Lookup-Antwort `result_kind`
Drei Werte: `found`, `found_with_caveats`, `not_in_corpus`. Steuert
die nächste Aktion (Verwendung, Disambiguierung, Re-Extraktion).

### M-Phasen
v1.0-Implementierung: M0 (Bootstrap) – M8 (Hardening). Status-
Tabelle in `implementation/mvp/00-index.md`.

### P-Phasen
v2.0-Migration: P0 (Vorbereitung) – P5 (Hardening + Tag).

### Dual-Write
v1→v2-Übergangsmechanik: jeder Schreibe-Pfad geht parallel in den
v1.0-SoT (SQLite/NATS) **und** den v2.0-Polyglot-Store; Drift wird
gemessen.

---

*Stand: 2026-05-08 · Greenfield-Initial · letzte Sektion offen für Erweiterung*
