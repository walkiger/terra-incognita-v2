# `M8-hardening-deploy.md` — Phase M8: Hardening & Deploy

> **Lebendiges Dokument.** Ergebnis: Public-Facing Schaufenster ist
> betriebsfest. Cloudflare-Tunnel gehärtet, mTLS-Engine-Cert produktiv,
> Rate-Limit / Quotas validiert, OOM-Schutz greifend, Backup-Restore-
> Drill bestanden, Multi-User-Smoke-Suite läuft, Alert-Rules aktiv.
>
> **Phase-Tag bei Abschluss:** `v0.9.0` (Pre-Release), Final-Tag:
> `v1.0.0`.

---

## Inhalt

1. [Phasen-Ziel](#1-phasen-ziel)
2. [Vorbedingungen](#2-vorbedingungen)
3. [Architektur-Bezug](#3-architektur-bezug)
4. [Schritte M8.1 – M8.9](#4-schritte-m81--m89)
5. [Phasen-Gate (v1.0.0 Release)](#5-phasen-gate-v100-release)
6. [Erledigte Änderungen](#6-erledigte-änderungen)

---

## 1. Phasen-Ziel

* **Cloudflare-Tunnel-Hardening**: WARP-bridged-only, Cloudflare Access
  für `/admin/*`, Geo-/Bot-Filter wo sinnvoll.
* **mTLS-Engine-Cert** ist nicht mehr Test-Cert, sondern wird über eine
  produktive Mini-CA ausgestellt (oder Cloudflare-Mtls-Pipeline).
* **Rate-Limit-Soak**: 24-Stunden-Stress-Test bestätigt korrekte
  Throttling-Verhalten ohne Memory-Wachstum.
* **OOM-Protection**: cgroups, swap-Off-Strategie, oom_score_adj
  funktionieren, einzelne Service-Kills passieren in der erwarteten
  Reihenfolge.
* **Backup-Restore-Drill**: tatsächlich auf einer fresh provisionierten
  VM in < 15 min produktiv.
* **Multi-User-Smoke**: 50 Browser-Connections + 5 Engine-Connections
  parallel über 10 min.
* **Observability-Alerts**: Alle in `architecture/mvp.md` §10
  formulierten Alerts feuern in Test-Setup, gelogged.
* **`v1.0.0`**: Tag, Release-Notes, finale Verifikation.

---

## 2. Vorbedingungen

* M0–M7 abgeschlossen, `v0.8.0` getaggt.
* Hub und Vault auf Oracle-VMs produktiv erreichbar.
* Frontend, Engine, Replay funktional.

---

## 3. Architektur-Bezug

* `architecture/mvp.md` §9 — Sicherheits-Threat-Modell
* `architecture/mvp.md` §10 — Beobachtbarkeit, Alerts
* `architecture/mvp.md` §11 — Deployment, Releases
* `architecture/mvp.md` §13 — Speicher-Budget (OOM-Reihenfolge)

---

## 4. Schritte M8.1 – M8.9

---

### M8.1 — cloudflared-tunnel-hardening

**Branch:** `feature/cloudflared-tunnel-hardening`
**Issue:** `#NNN`
**Vorbedingungen:** M0.5 gemerged
**Berührte Pfade:**
```
deploy/cloudflared/config.hub.yml             ← finale Settings
deploy/cloudflared/config.vault.yml           ← finale Settings
deploy/cloudflare/access-policies.md          ← Access-Policies dokumentiert
docs/operations/tunnel-hardening.md
tests/integration/test_tunnel_hardening.py
```

**Akzeptanzkriterien:**
1. **Cloudflare Access** auf `/v1/admin/*` und `/v1/diagnostic` (admin-
   sections) — Allowlist von E-Mail-Adressen.
2. **WAF-Regeln** (Cloudflare Free WAF):
   * Rate-Limit auf `/v1/auth/login` (10/min/IP) — komplementär zum
     Hub-internen Limit.
   * Block known-bad-IP-Lists (Cloudflare-Managed-Free).
3. `originRequest` Settings:
   * `connectTimeout: 10s`, `tlsTimeout: 10s`, `tcpKeepAlive: 30s`,
     `keepAliveTimeout: 90s`.
   * `noHappyEyeballs: false`.
4. **SSH-Bastion** über Cloudflared (`type: ssh`) ist eigener
   Tunnel-Eintrag, der nur Token-basiert nutzbar ist.

**Tests:**
* `tests/integration/test_tunnel_hardening.py::test_admin_route_requires_access`
* `tests/integration/test_tunnel_hardening.py::test_login_rate_limit_kicks_in`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~300 Lines diff
**Fertig wenn:** AC + CI grün; manuell bestätigt mit Burner-Account.

---

### M8.2 — mtls-engine-cert-issuance

**Branch:** `feature/mtls-engine-cert-issuance`
**Issue:** `#NNN`
**Vorbedingungen:** M2.4 gemerged
**Berührte Pfade:**
```
deploy/mtls/
├── README.md
├── ca/
│   ├── private.example.key                   ← Beispiel-Skelett, echte Keys in SOPS
│   └── ca.example.crt
└── issue.sh
docs/operations/engine-mtls.md                ← finale Doku
backend/api/security/mtls.py                  ← Cert-Pinning erweitert
```

**Akzeptanzkriterien:**
1. **Eigene Mini-CA** (offline, AGE-verschlüsselt) für Engine-Certs.
2. `issue.sh` erstellt:
   * Engine-Cert mit Subject `CN=<email>@engine.terra.tld`.
   * Lebensdauer 365 Tage.
   * SAN-Felder: `DNS:engine.<email>`.
3. **Distribution**: User bekommt sein Cert manuell via Admin-CLI;
   Self-Service kommt erst in v1.x.
4. **Revocation-Liste**: einfache Datei (`ca/revoked.txt`) — Hub liest
   sie alle 5 min ein.
5. **Cloudflare-Konfiguration** für mTLS-Mode auf
   `terra.<example>.tld/ws/v1/engine`.

**Tests:**
* `tests/integration/test_mtls_issuance.py::test_issued_cert_validates_at_hub`
* `tests/integration/test_mtls_issuance.py::test_revoked_cert_rejected`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~400 Lines diff
**Fertig wenn:** AC + CI grün; manuelles Issue-Cert + Connect erfolgreich.

---

### M8.3 — rate-limit-soak-tests

**Branch:** `test/rate-limit-soak-tests`
**Issue:** `—`
**Vorbedingungen:** M5.13 gemerged
**Berührte Pfade:**
```
tests/soak/
├── ratelimit_24h_simulator.py
├── ratelimit_burst_pattern.py
└── README.md
.github/workflows/nightly-soak.yml             ← bereits aus M0.7, hier konkretisiert
```

**Akzeptanzkriterien:**
1. Test-Skript simuliert:
   * 50 User mit jeweils 30 Encounter/min über 24 h.
   * 10 User mit Burst-Pattern (alle 5 min ein Burst von 200 req in 1 s).
2. Erwartung:
   * 429-Antworten in der dokumentierten Häufigkeit.
   * Hub-RAM-RSS bleibt stabil (Drift < 5 % über 24 h).
   * Keine 5xx-Spikes.
3. Skript läuft im Nightly-CI-Job; bei Verletzungen → Alert + Issue.

**Tests:** Soak-Job selbst.

**Ressourcen-Budget:** Soak-Job auf separater CI-Runner-Variante (oder
selbst-gehostet, falls nötig).
**Geschätzte PR-Größe:** ~400 Lines diff
**Fertig wenn:** AC + CI grün; ein 24-h-Lauf bestanden, Report
archiviert.

---

### M8.4 — oom-protection-cgroups

**Branch:** `chore/oom-protection-cgroups`
**Issue:** `#NNN`
**Vorbedingungen:** M0.3 gemerged
**Berührte Pfade:**
```
deploy/compose/hub.yml                       ← `oom_kill_disable`, `oom_score_adj` finalisiert
deploy/compose/vault.yml                     ← analog
docs/operations/oom-strategy.md
tests/integration/test_oom_strategy.py
```

**Akzeptanzkriterien:**
1. `oom_score_adj` pro Service (siehe `architecture/mvp.md` §11).
2. **Swap-Strategie**:
   * Oracle-AMD-Micro hat default 0 GB Swap. Wir aktivieren **2 GB
     Swap-File** auf `/swapfile` (cgroup-fähig). Swap reduziert
     OOM-Killraten unter Last, kostet keine RAM.
3. **`docker-compose`-`memswap_limit`** korrekt gesetzt: kein
   unkontrollierter Swap-Verbrauch auf Service-Ebene.
4. **Test**: Skript füllt Memory künstlich; Service mit höchstem
   `oom_score_adj` wird zuerst gekillt, andere überleben.

**Tests:**
* `tests/integration/test_oom_strategy.py::test_grafana_killed_first`
* `tests/integration/test_oom_strategy.py::test_api_survives_grafana_oom`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~300 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M8.5 — backup-restore-drill-doc

**Branch:** `docs/backup-restore-drill`
**Issue:** `#NNN`
**Vorbedingungen:** M1.11 gemerged
**Berührte Pfade:**
```
docs/operations/backup-restore-drill.md       ← Drill-Doku finalisiert
scripts/operations/restore_hub.sh             ← falls Anpassungen nötig
docs/operations/post-drill-report.md          ← Vorlage
```

**Akzeptanzkriterien:**
1. **Tatsächlicher Drill** wird durchgeführt:
   * Neue VM provisioniert.
   * Restore-Skript läuft.
   * Smoke-Test grün.
   * Zeit von „Provisioning fertig" bis „v1/health 200" gemessen.
2. **Erwartung**: < 15 min total.
3. **Post-Drill-Report** in `docs/operations/post-drill-report.md`
   (kann auch als `catchup.md`-Eintrag); enthält Probleme, Verbesserungs-
   Vorschläge.
4. **Hidden-Failure-Liste**: alle Schritte, die der Drill aufgedeckt
   hat (z. B. fehlende SOPS-Recipient, fehlende Doku) werden als Issue
   eröffnet und vor Tag `v1.0.0` adressiert.

**Tests:** Drill ist der „Test".
**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~250 Lines diff
**Fertig wenn:** AC + Drill abgeschlossen + Report committed.

---

### M8.6 — observability-alert-rules

**Branch:** `feature/observability-alert-rules`
**Issue:** `#NNN`
**Vorbedingungen:** M0.9 gemerged
**Berührte Pfade:**
```
deploy/prometheus/alert_rules.yml             ← aktive Regeln (war Beispiel)
deploy/grafana/provisioning/alerting/         ← Grafana-Alerting-Provisioning
docs/operations/alerts.md
tests/integration/test_alerts.py
```

**Akzeptanzkriterien:**
1. Alle Alerts aus `architecture/mvp.md` §10 sind als YAML-Regeln
   ausgeschrieben.
2. **Receiver**: E-Mail (über Cloudflare Email-Routing), optional Slack-
   Webhook (privater Channel).
3. **Acknowledge / Silence-Workflow** dokumentiert.
4. **Synthetischer Test**: Simulator macht z. B. Litestream-Lag künstlich
   groß; Alert feuert binnen 10 min im Test-Run.

**Tests:**
* `tests/integration/test_alerts.py::test_litestream_lag_alert_fires`
* `tests/integration/test_alerts.py::test_hub_ram_alert_fires`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~400 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M8.7 — multi-user-smoke-suite

**Branch:** `test/multi-user-smoke-suite`
**Issue:** `—`
**Vorbedingungen:** M5, M6, M7 grün
**Berührte Pfade:**
```
tests/smoke/multi_user/
├── browser_clients.py                        ← Playwright-basiert, parallel Tabs
├── engine_clients.py                          ← parallele Engine-Connects
└── runner.py
docs/operations/multi-user-smoke.md
```

**Akzeptanzkriterien:**
1. 50 parallele Browser-Sessions (über Playwright, Headless) loggen ein,
   navigieren zum Cockpit, halten WS offen 10 min.
2. 5 parallele Engines connecten und produzieren Encounters.
3. Erwartung:
   * Hub-RAM bleibt < 90 % Auslastung.
   * 0 % 5xx-Antworten.
   * Replay-Latenzen p95 < 800 ms.
   * Keine WS-Drops > 5 % der Verbindungen.
4. Report-Artifact: HTML mit Latenz-Heatmap, Drop-Liste, Resource-Charts.

**Tests:** Suite selbst.
**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~600 Lines diff
**Fertig wenn:** AC + CI grün; ein erfolgreicher 10-min-Lauf liegt vor.

---

### M8.8 — release-v1-checklist

**Branch:** `docs/release-v1-checklist`
**Issue:** `—`
**Vorbedingungen:** M8.1 – M8.7 gemerged
**Berührte Pfade:**
```
docs/releases/v1.0.0-checklist.md
.github/release-template.md
```

**Akzeptanzkriterien:**
1. Checklist enthält:
   * [ ] M0–M8 alle grün, Tags `v0.x.0` gesetzt.
   * [ ] OpenAPI v1.json eingefroren, Diff-Gate grün.
   * [ ] Numerical-Conformance-Suite grün.
   * [ ] Replay-Latenz-Gate grün.
   * [ ] Multi-User-Smoke 10 min bestanden.
   * [ ] Backup-Restore-Drill < 15 min bestanden.
   * [ ] Alert-Rules feuern wie erwartet.
   * [ ] CSP, mTLS, JWT-Pfade durch Test-Suite verifiziert.
   * [ ] Lade-Zeit Frontend < 2 s auf simuliertem 4G.
   * [ ] DSGVO-Endpunkt `DELETE /v1/me` funktioniert.
   * [ ] Doku-Linterkette grün.
   * [ ] `archive/legacy-docs/Implementierungen.Architektur.md` mit Greenfield-Stand
     aktualisiert.
   * [ ] `catchup.md` Release-Eintrag verfasst.
2. Vor Tag `v1.0.0` muss jede Checkbox abgehakt sein.

**Tests:** Checkliste durchlaufen.
**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~200 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M8.9 — tag-v1-0-0

**Branch:** `chore/tag-v1-0-0`
**Issue:** `—`
**Vorbedingungen:** M8.8 gemerged + Checkliste abgehakt
**Berührte Pfade:**
```
CHANGELOG.md
catchup.md                                   ← Release-Eintrag
docs/releases/v1.0.0-notes.md
```

**Akzeptanzkriterien:**
1. `CHANGELOG.md` enthält v1.0.0-Eintrag mit Commit-Liste seit v0.1.0.
2. `catchup.md` hat einen Eintrag „Greenfield v1.0 Release".
3. `git tag -a v1.0.0 -m "Greenfield MVP — Public Schaufenster"` und
   Push zum Remote.
4. CD-Workflow `cd-release.yml` baut signed Images, schreibt Release-
   Notes auf GitHub.
5. Manuelles Smoke nach Deploy: Hub und Vault erreichbar, Login
   funktioniert, Cockpit lädt.

**Tests:** Release-Smoke.
**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~150 Lines diff
**Fertig wenn:** Tag gepusht, Release-Notes online, manueller Smoke
grün.

---

## 5. Phasen-Gate (v1.0.0 Release)

`v1.0.0` ist genau dann „grün", wenn:

1. M8.1 – M8.9 in `00-index.md` auf `[x]`.
2. Release-Checkliste vollständig abgehakt.
3. Tag `v1.0.0` öffentlich, Release-Notes verfügbar.
4. Hub und Vault produktiv unter den erwarteten Hostnamen erreichbar.
5. **`archive/legacy-docs/Implementierungen.Architektur.md`** ist um eine neue Spalte
   „Greenfield-Stand v1.0" ergänzt.
6. **`catchup.md`** hat einen abschließenden Eintrag „terra-Greenfield-
   v1.0 abgeschlossen am yyyy-mm-dd".

---

## 6. Erledigte Änderungen

— *(noch leer)*

---

*Stand: 2026-05-08 · Greenfield-Initial · M8 noch nicht eröffnet*
