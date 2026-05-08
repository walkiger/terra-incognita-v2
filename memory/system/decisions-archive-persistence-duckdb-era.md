# decisions-archive — Persistence (DuckDB-era) appendix

> **Archiviert.** Auszug aus dem deprecated DEC **„Persistence store — DuckDB baseline; long-term evaluation (MongoDB etc.)“** in [`decisions.md`](decisions.md). Nur für historische Skalierungs-/Trade-off‑Diskussion; **v1.0‑Kanone** ist SQLite (**ADR‑001**).

---

### Rough scale extrapolation from current EN seed artefact (`knowledge/preseed_v2.json`)

Measured on disk (representative `_meta`): **per‑ lemma anchor rows**: **2302**, **aggregate relation stubs** (summed `[…] relations` lists): **~134 051**, **density**: ~**58 relation rows per anchor on average**, **whole preseed JSON file**: ~**14.3 MiB**. These numbers matter for **cold-start ingest** magnitude; runtime growth compounds with **Ghost resolution** + **Encounter** additions.

Assume **100 000** outbound API calls (dictionary / enrichment) over system life. Calls are partly **idempotent** (already materialised), partly **novel**. Let **r** = fraction of calls that yield a **net new high-value materialised lemma** with enrichment depth **similar on average** to current preseed richness (upper bound heuristic).

Illustrative order-of-magnitude (linear edge scaling is **worst‑case**, **not** simultaneous with full independence — overlap and Ghost collapse reduce totals):

| Regime `r` (novelty proxy) | ~Net‑new lemmas (rough) | ~Added relation stubs (same banding heuristik) | Intuition für Serialisierung „wie Preseed‑JSON“ |
|---------------------------|-------------------------|------------------------------------------------|------------------------------------------------|
| 1 % (`r`=0.01) | bis ~1000 | +10 ⁴ – 10 ⁵ | Zehn‑ bis wenige Zig‑MiB zusätzlich |
| 10 % (`r`=0.10) | ~10 000 | ~6 × 10⁵ (vor Dedupe stark nach unten korrektur) | O(10² MiB) komprimierte JSON‑Schätzung ohne Optimierung |
| 50 % (`r`=0.50; extreme) | ~50 000 | order 10⁶+ Kantenliste‑Einträge | Preseed‑als‑Monolit bricht ergonomisch zusammen |

**Interpretation:** Hunderttausend API‑Calls verschieben bei moderatem Neuigkeitsgrad die **Dominante Last** weniger zwischen „Mongo vs embedded SQL“ als zwischen **RAM‑residentem KG‑Graph**, **Queue‑Dedupe‑Policy**, und **wie viel Geschichte** ihr festhalten wollt. Der **Hub‑SQLite‑Pfad** (Greenfield) entscheidet primär Checkpointing/Observability, nicht Rohfetch‑Throughput.

### Mongo vs embedded SQL (high level technical trade-offs for *this project shape*) — historical framing

- **Embedded columnar/analytic engines (exemplar: DuckDB):** günstig für **Batch‑Analytics**, Snapshots‑als‑Tabellen/Parquet, SQL‑Adhoc, **single‑node** — typically **does not magically speed** iterative single‑relation OLTP ohne Schema‑Engineering.
- **MongoDB:** Vorteile meist dort, wo ihr **verteiltes Schreib‑Many‑Writers‑Cluster**, **flexibles Schema pro Dokument** pro Node/Encounter, HA mit Replikaten, oder **document‑centric** Produktintegrationspipelines benötigt. **„Schneller“** ist keine globale Aussage — ab **Netz‑Roundtrip‑Domäne + Index‑Warmheit** relativ zu In‑memory KG ist der DB‑Layer oft nicht der erste Flaschenhals für Erst‑Pfad Activation.

ADR trigger examples (pick one roadmap review): persisted graph rows > **5×10⁵**‑**10⁶** active edges with latency SLO breached; Ops move from **single VPS** zu **Fleet** HA; Snapshot restore dominiert Downtime; Ghost queue **crash‑safeness contract** mandates separate WAL store.
