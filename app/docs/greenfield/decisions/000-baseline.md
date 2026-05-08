# ADR-000 — Baseline & Lock-In: Greenfield-Plan, Pfad B (Thin-Shell auf 2× AMD Micro)

* **Status:** Accepted
* **Datum:** 2026-05-08
* **Bezug:** Greenfield-Plan in `app/docs/greenfield/`

## Context

Die Frage stand im Raum, ob der Greenfield-Plan ein „best-of-breed
Polyglot-Setup von Tag 1" anstrebt oder der harten Realität der
verfügbaren Hardware folgt. Verfügbar sind aktuell ausschließlich
2× Oracle-Always-Free-Tier-VMs vom Typ `VM.Standard.E2.1.Micro`
(1 OCPU, 1 GB RAM, 50 GB Disk). ARM-A1-Kapazität auf dem Konto ist
nicht abrufbar.

Drei Pfade wurden geprüft:

* **Pfad A** — ARM-A1-Free-Tier (12 GB RAM total, 4 OCPU). Nicht
  verfügbar laut Konto-Aussage.
* **Pfad B** — Thin-Shell-MVP auf 2× AMD-Micro: Server als
  „Schaufenster" (FastAPI, Auth, Persistenz, Replay), schwere
  Engine-Compute auf User-Workstation lokal, Kommunikation per
  WSS+mTLS.
* **Pfad C** — Hybrid mit Oracle Autonomous DB. Funktional
  attraktiv, scheitert am Engine-Compute-Bedarf und am
  Konto-Limit.

## Decision

Wir folgen **Pfad B**:

* v1.0 wird auf 2× AMD-Micro deployed (Hub VM-A + Vault VM-B), mit
  SQLite + Litestream + NATS + Cloudflare-Tunnel.
* Der Tick-Engine-Compute (LNN/EBM/KG) läuft **lokal** auf der
  User-Workstation als Python-Paket `terra-engine`.
* v2.0 ist die echte M4-Migration mit dem Polyglot-Stack
  (`architecture/production.md`).

## Consequences

* **Positiv:**
  * Kosten = 0 (Free-Tier + Free-Cloudflare-Tunnel).
  * Keine Abhängigkeit von einer noch nicht beschaffenen M4-Hardware.
  * Architektur ist von Anfang an „Server = öffentliches Gesicht,
    Engine = privates Gehirn", was sich konzeptuell sehr gut zur
    Drei-Pol-Bewusstseins­metapher fügt.
  * Migration nach v2.0 ist gut definiert (siehe ADR-008,
    `implementation/production.md` Phasen P0–P5).
* **Negativ:**
  * Engine-Compute braucht *lokale* Hardware → User-Onboarding-
    Hürde („Sie brauchen einen Mac/Linux mit Python und 2 GB
    RAM").
  * Multi-User-Power-Charts gehen erst in v2.0.
  * v1.0 zeigt nicht das volle Potential des Systems — sondern
    eine ehrliche Vorab-Bühne.
* **Neutral:**
  * Wir investieren keine Code-Pfade, die in v2.0 obsolet würden:
    der Polyglot-Stack ist als ADR-008 für v2.0 vorgemerkt, ohne
    in v1.0 implementiert zu werden.

## Alternatives Considered

* **Pfad A (ARM-A1-Free-Tier)** — wäre die elegantere Lösung
  gewesen, ist aber operativ nicht beschaffbar.
* **Pfad C (Oracle Autonomous DB Hybrid)** — würde Persistenz
  lösen, lässt aber den Engine-Compute-Mangel ungelöst.
* **Sofortiger M4-Kauf** — finanziell aktuell nicht abbildbar; die
  Architektur ist explizit so gebaut, dass die M4-Migration ohne
  Datenverlust möglich ist.

## References

* `app/docs/greenfield/README.md`
* `app/docs/greenfield/architecture/mvp.md`
* `app/docs/greenfield/architecture/production.md`
* `Anweisungen.md` §7 *Non-Negotiables*

---

*Greenfield-Initial-ADR.*
