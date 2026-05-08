# `runbooks/oom-and-capacity.md` — OOM-Schutz & Kapazitäts­steuerung

> **Zweck.** Operative Anleitung, wie auf 2× 1 GB AMD-Micro-VMs
> Kapazität, OOM-Schutz und Drift überwacht und korrigiert werden.
> Ergänzt `architecture/mvp.md` §Memory-Budgets und
> `architecture/observability.md`.

---

## Inhalt

1. [Wahres RAM-Budget pro Service](#1-wahres-ram-budget-pro-service)
2. [Linux-Kontrollen](#2-linux-kontrollen)
3. [SystemD-Memory-Limits](#3-systemd-memory-limits)
4. [Swap-Datei-Strategie](#4-swap-datei-strategie)
5. [`oom_score_adj` Reihenfolge](#5-oom_score_adj-reihenfolge)
6. [Watchdog & Auto-Restart](#6-watchdog--auto-restart)
7. [SQLite-spezifische Tuning-Schritte](#7-sqlite-spezifische-tuning-schritte)
8. [NATS-spezifische Tuning-Schritte](#8-nats-spezifische-tuning-schritte)
9. [Last-Tests & Soak-Plan](#9-last-tests--soak-plan)
10. [Eskalations­pfad](#10-eskalationspfad)

---

## 1. Wahres RAM-Budget pro Service

**Hub VM-A (1024 MiB Total):**

| Service           | Idle (RSS) | Burst-Toleranz | Notiz |
|-------------------|-----------:|---------------:|-------|
| Kernel + base     |     90 MiB |        110 MiB | reserviert |
| Caddy             |     35 MiB |         60 MiB |   |
| FastAPI Hub (uvicorn, 1 worker) | 220 MiB | 360 MiB | inkl. Pydantic, aiosqlite, jose |
| NATS              |     45 MiB |         70 MiB |   |
| Litestream        |     20 MiB |         30 MiB |   |
| Cloudflared       |     30 MiB |         45 MiB |   |
| Prometheus (lokal) |    50 MiB |         75 MiB |   |
| Grafana (optional)|    40 MiB |         60 MiB | nur bei Bedarf gestartet |
| Vector (Logs)     |     20 MiB |         30 MiB |   |
| Reserve           |    100 MiB |        120 MiB | Kernel-Cache, OS-Background |
| **Summe Idle**    |   **510 MiB** | **750 MiB**  |   |

> *Hinweis.* Grafana wird in v1.0 nur **on-demand** gestartet
> (`systemctl start grafana` für Inspektion); sonst bleibt sie aus,
> um RSS zu sparen.

**Vault VM-B (1024 MiB Total):**

| Service             | Idle (RSS) | Burst | Notiz |
|---------------------|-----------:|------:|-------|
| Kernel + base       |     90 MiB | 110 MiB |  |
| `r2-pull` worker    |     40 MiB |  60 MiB |  |
| `snapshot-processor`|     50 MiB |  80 MiB | bei Snapshot-Eingang |
| `nats-subscriber`   |     45 MiB |  70 MiB |  |
| `synthetic-checks`  |     25 MiB |  40 MiB |  |
| Prometheus-Scrape-Target | 30 MiB | 45 MiB |  |
| Reserve             |    150 MiB | 180 MiB |  |
| **Summe Idle**      |   **430 MiB** | **585 MiB** |  |

---

## 2. Linux-Kontrollen

**Sysctl** (`/etc/sysctl.d/99-terra.conf`):

```
vm.overcommit_memory = 2
vm.overcommit_ratio  = 80
vm.swappiness        = 20
vm.vfs_cache_pressure = 200
fs.file-max = 65536
```

* `overcommit_memory=2` zwingt Kernel, kein "optimistisches Overcommit"
  zu erlauben — `malloc()` schlägt früh fehl statt OOM.
* `swappiness=20` priorisiert RSS, nutzt Swap nur als Notbremse.
* `vfs_cache_pressure=200` reduziert Page-Cache, lässt mehr für
  RSS frei.

---

## 3. SystemD-Memory-Limits

Pro Service ein Drop-in (`/etc/systemd/system/<svc>.service.d/limits.conf`):

```ini
[Service]
MemoryHigh=<x>M
MemoryMax=<y>M
TasksMax=64
LimitNOFILE=4096
```

Beispielwerte (Hub):

| Service        | `MemoryHigh` | `MemoryMax` |
|----------------|--------------|-------------|
| `caddy`        |  60M         | 90M         |
| `fastapi-hub`  | 360M         | 480M        |
| `nats`         |  70M         | 90M         |
| `litestream`   |  30M         | 50M         |
| `cloudflared`  |  45M         | 60M         |
| `prometheus`   |  75M         | 100M        |
| `vector`       |  30M         | 45M         |

`MemoryMax` triggert OOM-Kill **dieses** Services lange bevor das
System gegen die globale Grenze läuft.

---

## 4. Swap-Datei-Strategie

* **Größe:** 1 GiB Swap-Datei `/var/swap.img`.
* **Zweck:** *nur* Notbremse, **kein** Workload-Swap.
* **Erstellung:**

  ```bash
  sudo fallocate -l 1G /var/swap.img
  sudo chmod 0600 /var/swap.img
  sudo mkswap /var/swap.img
  sudo swapon /var/swap.img
  echo '/var/swap.img none swap sw 0 0' | sudo tee -a /etc/fstab
  ```

* **Alarm:** `node_swap_used_bytes > 256 MiB` über 10 min →
  `A.SWAP.HIGH`-Alert.

---

## 5. `oom_score_adj` Reihenfolge

Wenn das System dennoch OOM trifft, soll der Kernel die *richtigen*
Services killen. Reihenfolge der "OOM-Lust" (höher = wird früher
gekillt):

| Service           | `oom_score_adj` |
|-------------------|-----------------:|
| `grafana`          | +500            |
| `vector`           | +400            |
| `prometheus`       | +300            |
| `cloudflared`      | +100            |
| `litestream`       |   0             |
| `nats`             |   0             |
| `fastapi-hub`      |  -100           |
| `caddy`            |  -200           |
| `sshd`             |  -800           |

Setzen via `OOMScoreAdjust=`-Drop-in.

---

## 6. Watchdog & Auto-Restart

* SystemD-Watchdog: jeder Service hat `WatchdogSec=30s`,
  `Restart=always`, `RestartSec=5s`.
* `start-limit` (5 Restarts in 60 s) schützt vor Crash-Loop.
* Bei `start-limit-hit` → Webhook-Alert, manueller Eingriff.

---

## 7. SQLite-spezifische Tuning-Schritte

* `PRAGMA journal_mode=WAL;` (per Migration M1.1).
* `PRAGMA synchronous=NORMAL;` (Trade-off Litestream → R2 deckt
  Disaster-Recovery ab).
* `PRAGMA mmap_size=64*1024*1024;` (64 MiB mmap, hilft Read-Workload).
* `PRAGMA cache_size=-32000;` (≈ 32 MiB Page-Cache).
* `PRAGMA temp_store=MEMORY;`.
* WAL-Size-Watch: bei `wal_bytes > 64 MiB` → `wal_checkpoint(TRUNCATE)`
  via Cron alle 5 min.
* Read-Side: Vault-Mirror öffnet DB **read-only** mit `nolock=1`,
  vermeidet WAL-Konflikte.

---

## 8. NATS-spezifische Tuning-Schritte

* JetStream-File-Storage `max_memory_store = 8 MiB`.
* `max_outstanding_acks = 1024` pro Consumer.
* Pull-Consumer mit `max_ack_pending = 256` für `nats-subscriber`.
* JetStream-Cluster: in v1.0 Single-Node; in v2.0 → 3-Replica auf M4.
* Lag-Alert: `terra_nats_stream_pending > 1000` für 5 min →
  `A.NATS.PENDING`.

---

## 9. Last-Tests & Soak-Plan

* **Vor jedem Release** Mini-Soak-Test:
  * 10× simulierte User parallel,
  * 50 Encounters / Min / User,
  * 30 min Dauer.
  * Erfolgs­kriterien:
    * `terra_process_rss_bytes{service="fastapi-hub"} < 480 MiB`,
    * keine OOM-Kills,
    * Replay-p95 < 1500 ms.
* **Quartalsweise** Lange-Soak (6 h) mit gleicher Last; zusätzliche
  Erfolgs­kriterien:
    * `terra_litestream_replication_lag_ms < 60 s` 99 % der Zeit,
    * Memory-Drift < 50 MiB über 6 h.

Skripte: `infra/loadtest/locustfile.py` (M8.3 Pflicht).

---

## 10. Eskalations­pfad

1. **Lokal beheben** (Schritte §1–§9).
2. **Geplant degradieren**:
   * Frontend zeigt "Wartungsmodus" (CSP + statische Seite via Caddy).
   * Engine-WS pausiert mit `1013 try_again`.
3. **Hardware-Eskalation**:
   * Falls Workload dauerhaft an der Grenze → Vault auf 2-VCPU-Shape
     wechseln (Free-Tier ARM `A1.Flex` mit ≤ 4 VCPU / 24 GB; in v1.0
     **nicht verfügbar** lt. Konto-Aussage 2026-05-08).
   * Falls dies wieder verfügbar → siehe `architecture/production.md`
     "Pfad A" (Migration auf ARM-Free-Tier vor M4-Hardware).
4. **Migrations­pfad zu v2.0 vorziehen**, falls Performance-Schmerz
   den Free-Tier-Vorteil aufwiegt.

---

*Stand: 2026-05-08 · Greenfield-Initial · referenziert aus
`architecture/mvp.md` und allen MVP-Phasen, in denen Kapazität
relevant ist (M0, M3, M5, M8).*
