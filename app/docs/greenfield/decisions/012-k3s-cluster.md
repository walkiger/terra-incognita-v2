# ADR-012 — k3s als v2.0-Cluster-Substrat

* **Status:** Proposed
* **Datum:** 2026-05-08
* **Bezug:** `architecture/production.md` §13,
  `implementation/production.md` §10 (P0).

## Context

In v2.0 müssen 8+ Stateful-Stores plus FastAPI-Hub plus Tick-Engine-
Pool zusammen orchestriert werden. Optionen:

* **Docker Compose** auf SystemD: einfach, aber Auto-Recovery
  begrenzt, kein Multi-Node.
* **Docker Swarm**: einfach, aber Marktbreite seit 2020 stark
  rückläufig — Helm-Equivalent fehlt.
* **k3s** (lightweight Kubernetes): Single-Binary, < 200 MiB
  Footprint, voll Helm-kompatibel.
* **Full Kubernetes (kubeadm)**: zu schwer für 1–2 M4 Nodes.

## Decision

**Vorgeschlagen:** k3s als v2.0-Cluster-Substrat.

* 1× M4 (Server + Worker), `role=hub`.
* 1× Vault (Worker), `role=vault`.
* Optional: 2. M4 als Replica.
* Helm-Charts unter `infra/helm/<service>/` für jeden Stateful-
  Store + Engine-Pool.
* External-Secrets-Operator + SOPS für Secret-Management.

Verifikation: in P0 (`implementation/production.md` §10 P0.2)
wird k3s lokal aufgesetzt und ein vollständiger Polyglot-Stack
deployed. Wenn die Operations-Last unzumutbar wird, fällt die
Entscheidung gegen k3s zurück auf Docker Compose mit SystemD.

## Consequences (vorläufig)

* **Positiv (erwartet):**
  * Helm-Marktbreite (Standard-Charts für Postgres, ClickHouse,
    Neo4j, Qdrant, Redpanda existieren).
  * Auto-Restart, Health-Checks, Rolling-Upgrades out-of-the-box.
  * Vault-Worker kann nahtlos integriert werden.
* **Negativ (erwartet):**
  * Cluster-Operations-Last (Etcd/SQLite-DB von k3s, Cert-
    Renewal). k3s reduziert das gegenüber kubeadm deutlich.
* **Neutral:**
  * Verfügbarkeit von Helm-Charts ist Tag 1 verifizier­bar.

## Alternatives Considered

* **Docker Compose**: ja, aber Multi-Node-Erweiterung schwierig.
* **Nomad + Consul**: HashiCorp-Stack, gute Eigenschaften, aber
  Helm-Equivalent fehlt; Marktbreite kleiner als k3s.

## References

* `architecture/production.md` §13
* `implementation/production.md` §10
* k3s-Doku: <https://k3s.io>

---

*Greenfield-Initial-ADR (vorgeschlagen, finalisiert in P0).*
