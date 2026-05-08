# `runbooks/operations.md` — Betriebs-Runbook

> **Zweck.** Tägliche/wöchentliche/monatliche Routinen sowie
> Eingriffsanleitungen für die häufigsten Reibungspunkte im v1.0-
> Betrieb. Komplementär zu `runbooks/disaster-recovery.md` und
> `runbooks/oom-and-capacity.md`.

---

## Inhalt

1. [Tägliche Routinen](#1-tägliche-routinen)
2. [Wöchentliche Routinen](#2-wöchentliche-routinen)
3. [Monatliche Routinen](#3-monatliche-routinen)
4. [On-Demand-Eingriffe](#4-on-demand-eingriffe)
5. [Releases & Rollbacks](#5-releases--rollbacks)
6. [Cloudflare-Tunnel-Operationen](#6-cloudflare-tunnel-operationen)
7. [User-Verwaltung (CLI)](#7-user-verwaltung-cli)
8. [Quota-Anpassung pro User](#8-quota-anpassung-pro-user)
9. [Engine-Cert-Operationen](#9-engine-cert-operationen)
10. [Logs sichten & filtern](#10-logs-sichten--filtern)

---

## 1. Tägliche Routinen

* **08:00** — Status-Check (manuell oder automatisiert):
  * `curl -fsS https://terra.example/health` → 200, `db_ok=true`.
  * Synthetic-Checks (siehe `architecture/observability.md` §9)
    grün (Cron prüft, schreibt nach `system_health`).
  * Grafana-Board "01 — Public Health" sichtbar grün.
* **12:00** — Backup-Watch:
  * `terra_litestream_replication_lag_ms < 60 s` letzte 24 h ≥ 99 %.
  * R2-Bucket-Größe Wachstum vs. Vortag im erwarteten Korridor
    (±20 %).
* **18:00** — Audit-Mirror:
  * Vault `audit-mirror` zeigt Lag < 5 min.
* **23:00** — Cron `nightly_cleanup` läuft erfolgreich
  (`replay_events`-Retention, `quota_usage`-Truncate).

---

## 2. Wöchentliche Routinen

* **Sonntag 09:00** — `pip-audit` + `npm audit` rerun (auch wenn CI
  läuft); Bericht in `memory/runtime/security-watch.md` ergänzen, wenn
  Findings.
* **Montag** — `trivy` Scan gegen aktuelle Images.
* **Mittwoch** — Manuelle Disk-Quoten Sichtprüfung (`df -h`); freier
  Disk ≥ 25 % auf beiden VMs.
* **Freitag** — Mini-Soak (siehe `oom-and-capacity.md` §9, 30 min).

---

## 3. Monatliche Routinen

* **DR-Drill** Szenario A (Hub-Disk-Loss) — `disaster-recovery.md`.
* **Cert-Watch**: alle Zertifikate (Cloudflare-Edge, Engine-CA,
  Engine-Client, JWT-Schlüssel) auf Restlaufzeit prüfen; Erneuerung
  bei < 30 d.
* **Quota-Review**: Top-10-User nach Snapshot-Bytes; auffällige
  Sprünge dokumentieren.
* **Memory-Drift-Review**: 6-h-Soak laufen lassen; Drift > 50 MiB
  als Issue eröffnen.

---

## 4. On-Demand-Eingriffe

### 4.1 Einzelnen User sperren

```sql
UPDATE users SET is_disabled = 1, updated_at_ms = strftime('%s','now')*1000
WHERE id = :user_id;

UPDATE refresh_tokens SET revoked = 1
WHERE user_id = :user_id AND revoked = 0;
```

### 4.2 Engine-Account abkoppeln

```sql
UPDATE engine_registrations SET is_active = 0
WHERE user_id = :user_id AND engine_id = :engine_id;
```

### 4.3 Replay-Cache flushen

```bash
sqlite3 /var/lib/terra/hub.db "DELETE FROM kv_cache WHERE scope='replay.window';"
```

### 4.4 Snapshot manuell als `is_active=0` markieren

```sql
UPDATE snapshots SET is_active = 0 WHERE id = :snapshot_id;
```

(Kein Hard-Delete; R2-Cleanup nur via `r2-purge`-Job.)

---

## 5. Releases & Rollbacks

### 5.1 Release-Schritte

1. **Tag** erstellen: `git tag v0.X.Y && git push --tags`.
2. **CI** Build erzeugt:
   * Hub-Image (Docker),
   * Engine-Wheel,
   * Frontend-Bundle (Cloudflare-Pages).
3. **Canary**: `cloudflared` Routing kann pro-`/path`-prefix-split
   testen → 5 % Traffic auf neue Version (M8.6 ergänzt).
4. **Promotion** nach Canary-Soak (≥ 1 h grün).
5. **Engine-Update**: optional; Engine-Wheel ist abwärts­kompatibel
   für mindestens eine Hub-Version.

### 5.2 Rollback

* **Container**: `docker tag terra-hub:vX.Y → :latest && systemctl restart`.
* **Frontend**: Cloudflare Pages "Deploy revert" auf vorherigen
  Build.
* **DB-Migration**: nur durch `alembic downgrade -1`; vorher
  Litestream-Stop + Backup.
* **Tag**: keinen `--force`-Push, sondern `vX.Y.Z+1`-Patch.

---

## 6. Cloudflare-Tunnel-Operationen

* **Logs**: `journalctl -u cloudflared -f`.
* **Health**: `cloudflared tunnel info <tunnel-id>` zeigt Connector-
  Anzahl. Erwartung in v1.0: 1 (Free-Tier).
* **Routen**:
  * Public: `terra.example` → `http://localhost:8080` (FastAPI hinter
    Caddy).
  * Engine-WS: `engine.terra.example` → `wss://localhost:8443` mit
    mTLS-Validation.
  * Admin: `admin.terra.example` → `http://localhost:8081` (separater
    Route mit IP-allow-list als Defense-in-Depth).
* **Token-Rotation**: alle 180 d; Schritte:
  1. `cloudflared tunnel token create <tunnel-id>` (neuer Token).
  2. SOPS-Update.
  3. `systemctl reload cloudflared`.
  4. Alter Token revoken via Dashboard.

---

## 7. User-Verwaltung (CLI)

CLI: `scripts/admin.py`.

```bash
# User-Liste
py scripts/admin.py users:list --limit 50

# User anlegen (für interne Tests)
py scripts/admin.py users:create \
  --email me@example.com --display-name "Me" --lang de \
  --password 'TempStrong#1' --send-set-pw-link

# User promoten
py scripts/admin.py users:promote --user-id 42

# User löschen (DSGVO-Hard-Delete)
py scripts/admin.py users:delete --user-id 42 --confirm
```

Alle Aufrufe schreiben Audit-Einträge.

---

## 8. Quota-Anpassung pro User

Standard-Quotas in `config/quotas.json`. Override pro User:

```sql
INSERT OR REPLACE INTO settings(user_id, key, value, updated_ms)
VALUES (:user_id, 'quota.snapshot.bytes_30d', '5368709120', :now);
```

Audit:

```sql
INSERT INTO audit_log(ts_ms, actor_user_id, action, target_kind, target_id, meta_json)
VALUES (:now, :admin_user_id, 'admin.quota.update', 'user', :user_id,
        json_object('key','quota.snapshot.bytes_30d','value','5368709120'));
```

---

## 9. Engine-Cert-Operationen

### 9.1 Engine enrollen

```bash
py scripts/admin.py engine:enroll \
  --user-id 42 --engine-id macbook-pro-001 \
  --csr ./pending/macbook-pro-001.csr \
  --validity-days 365
```

* Erzeugt Cert (Engine-CA-signiert).
* Speichert Thumbprint in `engine_registrations`.

### 9.2 Engine deaktivieren

```sql
UPDATE engine_registrations SET is_active = 0
WHERE user_id = 42 AND engine_id = 'macbook-pro-001';
```

### 9.3 Cert rotieren

* Neuen CSR akzeptieren (gleicher engine_id), Thumbprint überschreiben.
* Alten Thumbprint 14 Tage in einer Sperr-Tabelle (`revoked_engine_certs`)
  führen, danach hart löschen.

---

## 10. Logs sichten & filtern

### 10.1 Lokal

```bash
# nur HTTP-Errors
journalctl -u fastapi-hub -o json --since "1 hour ago" | \
  jq -r 'select(.MESSAGE | fromjson | .status >= 500)'

# nur ein User
journalctl -u fastapi-hub -o json --since "1 hour ago" | \
  jq -r 'select(.MESSAGE | fromjson | .user_id == 42)'

# WS-Reconnect-Storm sichten
journalctl -u fastapi-hub -o json --since "10 min ago" | \
  jq -r 'select(.MESSAGE | fromjson | .event == "ws.close" and .reason != "client_close")'
```

### 10.2 R2-Mirror durchsuchen

```bash
aws s3 sync s3://terra-incognita-mvp/audit/year=2026/month=05/ ./audit-tmp/ \
  --endpoint-url https://<account>.r2.cloudflarestorage.com

zcat audit-tmp/day=08/*.jsonl.gz | jq -r 'select(.action=="snapshot.upload")'
```

---

*Stand: 2026-05-08 · Greenfield-Initial · referenziert aus
`architecture/security.md` §11, `architecture/observability.md`,
`runbooks/disaster-recovery.md`, `runbooks/oom-and-capacity.md`.*
