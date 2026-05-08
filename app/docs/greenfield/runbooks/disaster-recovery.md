# `runbooks/disaster-recovery.md` — Disaster Recovery

> **Zweck.** Schritt-für-Schritt-Wiederherstellung nach den
> realistischen Verlust­szenarien für die v1.0-Topologie
> (Hub VM-A + Vault VM-B + R2 + Cloudflare-Tunnel).
>
> **Zielgrößen** (RTO/RPO) für v1.0:
>
> * RTO (Recovery Time Objective): **≤ 60 min** für Hub-Wiederaufbau.
> * RPO (Recovery Point Objective): **≤ 60 s** Daten­verlust durch
>   Litestream-Streaming nach R2.
>
> Übung: monatlich (M8.5 Pflicht; danach in `runbooks/operations.md`
> als Wiederholungs-Plan).

---

## Inhalt

1. [Szenario-Übersicht](#1-szenario-übersicht)
2. [Vorbedingungen & Werkzeuge](#2-vorbedingungen--werkzeuge)
3. [Szenario A — Hub-Disk-Loss](#3-szenario-a--hub-disk-loss)
4. [Szenario B — Hub-VM komplett verloren](#4-szenario-b--hub-vm-komplett-verloren)
5. [Szenario C — Vault-VM verloren](#5-szenario-c--vault-vm-verloren)
6. [Szenario D — R2-Outage](#6-szenario-d--r2-outage)
7. [Szenario E — Cloudflare-Tunnel-Outage](#7-szenario-e--cloudflare-tunnel-outage)
8. [Szenario F — Korruption der SQLite-DB](#8-szenario-f--korruption-der-sqlite-db)
9. [Szenario G — Geheimnis-Kompromittierung](#9-szenario-g--geheimnis-kompromittierung)
10. [Drill-Plan & Berichts-Template](#10-drill-plan--berichts-template)

---

## 1. Szenario-Übersicht

| Szenario | Eintrittswahrscheinlichkeit | RTO | RPO  |
|----------|------------------------------|------|-------|
| A — Hub-Disk-Loss        | mittel  | 60 min  | 60 s  |
| B — Hub-VM verloren      | mittel  | 90 min  | 60 s  |
| C — Vault-VM verloren    | niedrig | 120 min | 5 min |
| D — R2-Outage            | niedrig | n/a (R2-SLA) | 0 s |
| E — Tunnel-Outage        | niedrig | 30 min  | 0 s   |
| F — DB-Korruption        | niedrig | 60 min  | 60 s  |
| G — Secret-Kompromittierung | niedrig | 4 h | 0 s   |

---

## 2. Vorbedingungen & Werkzeuge

* Lokal eingerichtet:
  * `oci`-CLI (Oracle), Login-Profil mit IaaS-Recht.
  * `cloudflared`-CLI mit Konto-Token.
  * `aws`-CLI gegen R2 (S3-kompatibles Endpoint).
  * `litestream` (≥ 0.3.x) Binary.
  * `sops` + `age`-Keys (mind. 2 Empfänger online).
  * Engine-CA-Privat­schlüssel **offline** verfügbar (Yubikey/USB).
* Im Repo:
  * `infra/ansible/` Playbooks `bootstrap_hub.yml`,
    `bootstrap_vault.yml`, `restore_hub.yml`.
  * `runbooks/disaster-recovery.md` (dieses Dokument).
  * `secrets/*.enc.yml` (SOPS).
* Externe Quellen:
  * R2-Bucket `terra-incognita-mvp` mit `litestream/` und
    `snapshots/`.
  * Audit-/Health-Mirror unter `audit/` und `health/`.

---

## 3. Szenario A — Hub-Disk-Loss

**Ereignis.** Die Disk der Hub-VM ist beschädigt; Datei­system
nicht mehr lesbar; VM selbst läuft aber.

**Schritte.**

1. **Stop** alle Services auf VM-A:
   ```bash
   sudo systemctl stop fastapi-hub nats litestream caddy cloudflared
   ```
2. **Mount** neue Disk (oder `oci` Volume neu attachen, formatieren).
3. **Restore** aus R2 mit Litestream:
   ```bash
   litestream restore -if-replica-exists \
     -o /var/lib/terra/hub.db \
     s3://terra-incognita-mvp/litestream/hub.db
   ```
4. **Validate** DB:
   ```bash
   sqlite3 /var/lib/terra/hub.db "PRAGMA integrity_check;"
   ```
   Erwartung: `ok`.
5. **Start** Services in Reihenfolge:
   * `nats` (jetstream-Datenpfad ist verloren — wird neu aufgebaut,
     Backlog ist akzeptabel).
   * `fastapi-hub`.
   * `caddy`.
   * `cloudflared` (Tunnel-Token aus SOPS dekodiert).
6. **Run** Smoke-Test (`scripts/smoke/health.sh`).
7. **Notify** Nutzer-/Engine-Bestand: WS-Reconnect-Storm zu erwarten.

**RTO-Erwartung:** 60 min.

---

## 4. Szenario B — Hub-VM komplett verloren

**Ereignis.** Hub-VM nicht mehr erreichbar (Provider-Outage,
Account-Sperrung, …).

**Schritte.**

1. **Provision** neue VM (Oracle Free Tier oder beliebiges Substrat
   mit ≥ 1 GB RAM, 50 GB Disk):
   ```bash
   oci compute instance launch --availability-domain ... \
     --image-id ... --shape VM.Standard.E2.1.Micro \
     --display-name terra-hub-replacement
   ```
2. **Bootstrap** mit Ansible:
   ```bash
   ansible-playbook -i inventory/free-tier.yml \
     infra/ansible/bootstrap_hub.yml \
     --extra-vars "hub_host=<new-ip>"
   ```
   * Installiert: Caddy, FastAPI-Hub-Wheel, NATS, Litestream,
     Cloudflared.
   * Pflegt SystemD-Units, sysctl-Tuning, OOM-Score-Adjust.
3. **Restore** wie in Szenario A Schritt 3–5.
4. **Cloudflare-Tunnel re-routen**:
   * `cloudflared tunnel route dns <tunnel-id> <hostname>` mit dem
     bestehenden Tunnel-Token (Token re-use ist erlaubt; im Doubt:
     neuer Token, Hostname-Update binnen 5 min).
5. **Engine-Reconnect-Bestätigung** (Heartbeat-Subjekte ankommen).
6. **Audit** Eintrag `incident.hub_replaced`.

**RTO-Erwartung:** 90 min.

---

## 5. Szenario C — Vault-VM verloren

**Ereignis.** Vault-VM weg.

**Schritte.**

1. **Provision** neue VM (gleicher Shape, 1 GB RAM).
2. **Bootstrap** mit `bootstrap_vault.yml`.
3. **Erst-Sync** `r2-pull` Job läuft an, holt aus R2:
   * `litestream/`-Streams (Read-Only-Mirror der Hub-DB).
   * `snapshots/` Index (kein blob-Download nötig, presigned-URLs
     funktionieren ad hoc).
   * `audit/` und `health/` (last 30 d).
4. **Validate** Read-Mirror via:
   ```bash
   sqlite3 /var/lib/terra/hub.read.db "SELECT COUNT(*) FROM replay_events;"
   ```
   Erwartung: vergleichbar mit Hub-Counter (max 60 s Lag).
5. **Synthetic-Checks** (siehe `architecture/observability.md` §9)
   schalten von "stale" auf "ok".

**RTO:** 120 min, RPO: 5 min (R2-Polling-Intervall).

---

## 6. Szenario D — R2-Outage

**Ereignis.** R2 ist erreichbar, aber Operationen laufen ins Leere
(SLA-Verstoß).

**Schritte.**

1. **Litestream**: Hub-DB läuft weiter; Litestream akkumuliert WALs
   lokal (`/var/lib/litestream/wal-buffer`); Alert
   `A.LITESTREAM.STALL` feuert nach 10 min.
2. **Snapshots**: Engine-Uploads schlagen mit `503 r2_unavailable`
   fehl; Engine pausiert Auto-Snapshot, fällt in einen Retry-
   Backoff (max 1 Versuch / 30 min).
3. **Audit-Mirror**: Audit-Events bleiben lokal (Vector-Buffer);
   Alert `A.AUDIT.MIRROR.LAG` feuert nach 10 min.
4. **Watch** R2 Status-Page; bei Wiederherstellung:
   * `litestream replicate` setzt fort.
   * `audit-mirror` flushed Buffer nach R2.

**Schmerzpunkt:** Keine Wiederherstellung möglich, solange R2 down.
Drill ohne R2 möglich, weil Litestream-Stop simulierbar
(`systemctl stop litestream`).

---

## 7. Szenario E — Cloudflare-Tunnel-Outage

**Ereignis.** Tunnel-Endpoint nicht erreichbar.

**Schritte.**

1. **Diagnose**:
   * `cloudflared tunnel info <id>` zeigt Status.
   * `journalctl -u cloudflared` für lokale Fehler.
2. **Sofortmaßnahmen**:
   * Tunnel restart: `systemctl restart cloudflared`.
   * Bei Persist: Token rotieren, neu enrollen.
3. **Fallback**: Direct-IP über `ufw allow 443/tcp from
   <admin-ip-only>` für Notfall-Admin-Zugriff (kein Public-DNS
   ändern).
4. **Notify** Nutzer per Status-Page.

**RTO:** 30 min.

---

## 8. Szenario F — Korruption der SQLite-DB

**Ereignis.** `PRAGMA integrity_check;` meldet Fehler.

**Schritte.**

1. **Stop** Schreib-Pfade (`fastapi-hub`, `nats-subscriber`).
2. **Snapshot** der korrupten DB nach `/var/lib/terra/hub.corrupt.db`
   (forensisch).
3. **Restore** wie in Szenario A Schritt 3.
4. **Replay-Lag**: NATS-Subjekt `engine.events.*` hält noch 7 d
   Backlog; nach Restore konsumieren wir alle Events seit
   `taken_at_ms` der wiederhergestellten DB.
5. **Validate** Replay-Window-Abdeckung (Counter vergleichen mit
   Vault-Mirror).

**RTO:** 60 min, RPO: 60 s.

---

## 9. Szenario G — Geheimnis-Kompromittierung

**Ereignis.** Verdacht, dass JWT-Schlüssel, Engine-CA, R2-Master oder
Cloudflare-Token kompromittiert sind.

**Sofortmaßnahmen.**

1. **JWT-Schlüsselrotation**: neuen `kid` aktivieren; alten `kid`
   in `auth/jwks.json` aber zunächst lassen, damit Refresh-Tokens
   migriert werden können (15 min Gnadenfrist).
2. **Refresh-Token-Massen­revoke**: alle Familien für betroffene
   User (oder global).
3. **Engine-CA-Rotation**: neue CA-Keys, alle Engine-Certs neu
   ausstellen; alte Cert-Thumbprints in `engine_registrations`
   `is_active=0` setzen.
4. **R2-Master-Rotation**: `kek_id` bumpt, neue Snapshots werden mit
   neuem KEK gewrappt; alte Snapshots bleiben mit altem KEK
   entschlüsselbar (KEK-Rolllover-Pfad in `architecture/security.md`
   §8 dokumentiert).
5. **Cloudflare-Tunnel-Token-Rotation**: neuen Token, Tunnel
   restart, alten Token revoken.
6. **Audit-Eintrag** + Post-Mortem (siehe §10).

**RTO:** 4 h (Cert-Reissue ist die längste Achse).

---

## 10. Drill-Plan & Berichts-Template

* **Frequenz**: monatlich, immer Szenario A vollständig + ein
  rotierendes weiteres.
* **Quartal**: Szenario B (vollständig).
* **Halbjahr**: Szenario G (Tabletop, kein Live-Rollout).
* **Bericht** unter `app/docs/greenfield/runbooks/drills/<YYYY-MM>.md`:

```markdown
# Drill <YYYY-MM>

## Szenarien
- A — Hub-Disk-Loss (live)
- F — DB-Korruption (live)

## Beobachtungen
- RTO Ist: 47 min
- RPO Ist: 38 s
- Auffälligkeiten:
  - litestream restore brauchte 6 min wegen großer WAL-Liste
  - Cloudflare-Tunnel re-routing-Schritt war doppelt dokumentiert

## Maßnahmen
- [ ] Issue `#NNN` Tunnel-Schritt deduplizieren
- [ ] PR `#NNN` Litestream-Doku ergänzen
```

---

*Stand: 2026-05-08 · Greenfield-Initial · referenziert aus
`architecture/security.md` §11 sowie M8.5.*
