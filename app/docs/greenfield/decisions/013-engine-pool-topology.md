# ADR-013 — Engine-Pool-Topologie (1 Prozess pro Tenant, idle-suspend)

* **Status:** Proposed
* **Datum:** 2026-05-08
* **Bezug:** `architecture/production.md` §12.9,
  `implementation/production.md` §6.

## Context

In v2.0 läuft der Tick-Engine-Compute (LNN/EBM/KG) auf der Server-
Hardware. Optionen für die Ausführungs-Topologie:

* **Multi-Tenant-Engine-Prozess:** Ein Python-Prozess hält die
  Tenant-Tabellen aller aktiven User. Vorteil: weniger Prozesse;
  Nachteil: GIL-Limit bei Tick-Hot-Path, Cross-Tenant-Memory-
  Korrelation.
* **1-Prozess-pro-Tenant (Engine-Pool):** Ein dedizierter Python-
  Prozess pro aktivem User, idle-suspended nach 10 min Inaktivität.
  Vorteil: harte Isolation, klare cgroup-Limits; Nachteil: höherer
  RAM-Footprint pro Tenant.
* **Threadpool im Hub:** würde GIL-blockieren, kein realistischer
  Pfad.

## Decision

**Vorgeschlagen:** 1-Prozess-pro-Tenant mit Engine-Pool-Manager.

* **Lifecycle:**
  * `start-on-demand`: bei erstem Engine-Subscribe oder
    `POST /v1/engine/spawn`.
  * `idle-suspend` nach 10 min ohne Encounter / Heartbeat / Snapshot.
  * `hard-kill` nach 60 min Inaktivität (Snapshot wird vorher
    geschrieben).
* **Begrenzung:**
  * Max 25 parallele Tenant-Prozesse auf einem M4 (≥ 96 GB RAM,
    Engine-RSS-Profil ~1.5 GB pro Tenant unter Volllast).
  * cgroup `memory.max = 2 GiB`, `cpu.max = 200000 100000`
    (= 2 vCPU).
* **Beschleunigung:**
  * Optional MPS (Apple Silicon GPU) für PyTorch-Tensoren.
  * Free-Threaded Python (PEP 703) wird in P0/P1 evaluiert
    (siehe `implementation/production.md` §9).

## Consequences (vorläufig)

* **Positiv (erwartet):**
  * Klare Tenant-Isolation; ein Engine-Crash betrifft nur einen
    Tenant.
  * cgroup-Limits schützen den Hub-Prozess gegen
    Tenant-Memory-Run.
  * Auto-Suspend reduziert Ruhe-Last des Pools.
* **Negativ (erwartet):**
  * Bei 25 aktiven Tenants und ~1.5 GB RSS = 37 GB Belegung —
    M4 mit 96 GB hat Reserve, aber Skalierung darüber nicht trivial.
* **Neutral:**
  * Reine Multi-Tenant-Engine kann immer noch als Optimierung in
    v2.5 evaluiert werden.

## Alternatives Considered

* **Multi-Tenant-Engine** (s.o.): GIL-Limit + Memory-Korrelation.
* **Container-pro-Tenant**: höhere Granularität, aber Operations-
  Last nochmals höher (eigene k3s-Pods pro Tenant).

## References

* `architecture/production.md` §12.9
* `implementation/production.md` §6, §9
* PEP 703 — Free-Threaded Python

---

*Greenfield-Initial-ADR (vorgeschlagen, finalisiert in P0/P1).*
