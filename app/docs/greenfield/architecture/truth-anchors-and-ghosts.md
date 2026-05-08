# `architecture/truth-anchors-and-ghosts.md` — Truth Anchors, Seeds → Geist, API‑Growth

> **Lebendiges Dokument.** Produkt‑ und Daten‑Semantik für „was ist wahr genug,
> dass das System darauf bauen darf". Ergänzt `mvp.md` (Technik) und
> `00-glossary.md` (Begriffe).

---

## 1. Zwei Truth Anchors (Reihenfolge der Priorität)

### Anchor A — **Externe lexikalisch‑relationale Wahrheit** (API / Seeds)

* **Quelle:** strukturierte Fremd‑APIs (z. B. Wörterbuch/Relations‑Dienste), die
  ihr Rate‑Limit und ihre Lizenz vorgeben.
* **Rolle:** **Breite und Konsistenz** des Graphen — „die Sprache und ihre
  üblichen Nachbarschaften existieren so in der Welt".
* **Persistenz:** **append‑only + Versionierung**: jede erfolgreiche Antwort
  wird dauerhaft persistiert (Roh‑Payload + Normalform + Abruf‑Metadaten:
  Zeitstempel, Quota‑Bucket, `request_id`, Hash). Kein Überschreiben ohne neue
  Version (`truth_revision` oder Event‑Sourcing).
* **Growth‑Modell:** kontrolliertes **permanentes Wachstum** bis zur API‑Grenze:
  Scheduler mit Backoff, Retry, Dedupe nach `(source, normalized_key)`. Ziel:
  irgendwann ist der erlaubte Umfang der Quelle **vollständig** im eigenen
  Store — dann ist der Anchor „saturiert", aber weiterhin historisch belegbar.

### Anchor B — **Formale Wahrheit** (Mathematik → Physik/Chemie/Biologie …)

* **Quelle:** kuratierte Literatur (PDF), extrahierte Formeln (`F.*`‑Registry,
  `research/extracted/`), später direkte DB‑/Korpus‑Anbindung.
* **Rolle:** **Wahr/Falsch‑ und Konsistenz­schicht** für Aussagen, die sich auf
  Gesetze, Definitionen und Mess­größen beziehen — nicht auf Meinung.
* **Persistenz:** eigene **Evidence‑ und Formula‑Stores** (v1: SQLite‑Tabellen +
  Dateien; v2: siehe `production.md` Polyglot). Jede nutzbare Formel hat:
  `F.*`‑ID, Status, Tests, PDF‑Evidence.

**Konsequenz für das MVP:** Beide Anchors müssen **modeliert** sein (Tabellen,
Jobs, Idempotenz), auch wenn die Ausbaustufen zuerst nur Seeds (A) und Registry
(B) abdecken.

---

## 2. Seeds → Geist (Ghost) — Minimal‑Semantik

Ein **Seed** ist ein Eintrag aus der erfolgreichen Vorab‑Fetch‑Pipeline (aktuelle
Nutzung). Ein **Geist** (`Ghost`) ist die **begehbare Repräsentation** dieses
Seeds im System:

| Phase | Bedeutung |
|-------|-----------|
| **materialisiert** | Knoten/Edges aus Seed sind im KG angelegt (evtl. mit niedrigem Gewicht / Tier T0). |
| **aufgelöst** | Encounter oder Inferenz hat den Ghost mit Nutzer‑Kontext verbunden → Kanten stärker, Tier‑Shift, Well‑Kandidaten. |
| **verdrängt / dormant** | Bessere Evidence oder Konflikt‑Policy hat den Ghost zurückgestellt (`make_dormant`‑Analog auch für Ghost‑Layers — siehe Haupt‑Architektur `Ghost`). |

**Zwei Auflösungswege (wie von dir beschrieben):**

1. **Direkt beim Seeding:** deterministische Projektion Seed → KG/EBM‑Setup +
   optional LNN‑Input‑Kanal (Breite zuerst).
2. **Nachgelagert:** Queue „Ghost‑Priorität“ — Background‑Fetcher/Worker holt
   nach und projiziert (gleiche Persistenz‑ und Idempotenz‑Regeln wie Anchor A).

Alles, was von der API kommt und gespeichert wird, fließt in denselben
**Evidence‑ und Lineage‑Pfad** (Auditierbarkeit für späteres „wahr/falsch").

---

## 3. Datenbanken: eine oder mehrere?

| Concern | v1.0 (Thin‑Shell) | Richtung v2.0 |
|---------|-------------------|----------------|
| Nutzer, Sessions, Replay, Quotas | SQLite (Hub) | Postgres |
| API‑/Seed‑Roharchive + Lineage | SQLite‑Tabellen + Objekt‑Storage‑Blobs | Postgres + MinIO/R2 + ClickHouse für Analytics |
| Formeln + Evidence | SQLite + `research/extracted/` | Postgres/JSON + OpenSearch + dedizierte Formula‑DB‑Spalten |
| KG‑Queries auf großem Graphen | Engine‑lokal / kompakt | Neo4j (+ GDS) |

**Antwort:** Ja, **mehrere Speicher** sind sinnvoll — aber im MVP **begrenzt**
(SQLite + Files + R2), schema‑mäßig aber **so trennen**, dass Migration ohne
Semantikverlust möglich ist (`data-model.md`).

---

## 4. Automatisierung und „direkt auf die Datenbank“

Vorbereitung bereits im MVP:

1. **Ingress‑Schicht:** alle Fetcher schreiben über eine kleine **Repository‑API**
   (nicht ad‑hoc SQL im Skript), mit Dedupe und `source_trust_level`.
2. **Job‑Queue:** NATS/Simple‑Table‑Queue für „fetch_next_seed",
   „expand_ghost", „reconcile_quota" — später Redpanda ohne Semantikbruch
   (`protocols/event-log.md`).
3. **DB‑gebundene Dokumenten‑Pipeline ( später ):**
   * Worker liest PDF‑Metadaten / Extraktionsjobs aus DB;
   * ruft `research-agent` bzw. Batch‑Extraktion auf;
   * schreibt `document_id`, Layer‑Status, `F.*`‑Links zurück.
4. **Truth‑Evaluator ( später ):** Regeln, die Aussagen gegen Anchor B (Formeln)
   und Anchor A (Lexikon/Relations) prüfen — Schnittstelle festlegen, Implementierung
   kann Stub sein.

Damit ist „irgendwann direkt loslassen“ **konfigurations‑ und schema‑ready**, nicht
nur Skript‑hocke.

---

## 5. Haben wir alles für „Auto‑Modus“ weiter?

**Technisch dokumentiert:** Ja für Architektur, Phasen, Verträge, Runbooks,
Formeln, ADRs unter `app/docs/greenfield/`.

**Noch offen für echte Automation ohne Mensch:**

| Thema | Status |
|-------|--------|
| Konkrete Seed‑/Ghost‑Tabellen + Migration | als nächster Implementierungs‑Schritt nach M1‑Schema‑Freeze definieren |
| API‑Keys, Quotas, Rate‑Shapes pro Quelle | Secrets + Konfig (SOPS) |
| Exakte Ghost‑Policy (wann materialisieren vs. queue) | Produktentscheid — hier nur Rahmen |
| Truth‑Evaluator‑API | Konzept oben; Code später |

**Designfragen (bewusst extra):** Ghost‑UX im Cockpit, Konflikt‑UI wenn Anchor A
vs. Nutzer‑Encounter kollidieren, Trust‑Decay über Zeit — gehören in eine kurze
Produktsession, nicht in dieses Architektur‑Stub‑Doc.

---

## Querverweise

* `architecture/mvp.md` — Deployment und Thin‑Shell
* `architecture/data-model.md` — Tabellen‑Spielraum
* `formulas/registry.md`, `protocols/pdf-lookup.md` — Anchor B
* `implementation/mvp/M1-data-foundation.md` — wo Persistenz ansetzt

---

*Stand: 2026-05-09 · eingeführt mit Umzug nach `app/docs/greenfield/`*
