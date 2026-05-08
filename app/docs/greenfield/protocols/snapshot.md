# `protocols/snapshot.md` — Engine-Snapshot-Protokoll

> **Zweck.** Vollständige Spezifikation des Snapshot-Formats, der
> Upload-Choreographie zwischen Engine und Hub, der server­seitigen
> Verifikation und der Restore-Pfade.
>
> **Geltung.** Eingefroren ab v0.3.x (M2). Format-Version-Schritte
> erfordern dual-read-Pfad analog zur Replay-API.

---

## Inhalt

1. [Container-Format `tar.zst`](#1-container-format-tarzst)
2. [Manifest-JSON (`manifest.json`)](#2-manifest-json-manifestjson)
3. [Inhalts-Layout pro Domäne](#3-inhalts-layout-pro-domäne)
4. [Upload-Sequenz](#4-upload-sequenz)
5. [Verifikation server­seitig](#5-verifikation-serverseitig)
6. [Verschlüsselung](#6-verschlüsselung)
7. [Restore-Sequenz](#7-restore-sequenz)
8. [Format-Versionierung](#8-format-versionierung)
9. [Fehlermodi & Recovery](#9-fehlermodi--recovery)
10. [Beispiele](#10-beispiele)

---

## 1. Container-Format `tar.zst`

* **Kompression:** Zstandard, Level 19 (Engine), Level 1 (Hub-
  Re-Upload, falls nötig).
* **Maximale Größe:** 256 MiB pro Snapshot in v1.0 (Hub-Quota
  `snapshot.bytes_30d` weiter limitierend).
* **Streamable:** ja; Hub kann inhaltlich Manifest entpacken **bevor**
  alle Inhalts-Dateien geladen sind.
* **Naming:** `snap_<unix_ms>_<6char-base32>.tar.zst`.

---

## 2. Manifest-JSON (`manifest.json`)

### 2.1 Schema (eingefroren ab v0.3.x)

```json
{
  "$schema": "https://schemas.terra.local/snapshot/v1.0.0.json",
  "snapshot_id": "snap_1714900000000_abc123",
  "format_version": "v1.0.0",
  "engine_id": "macbook-pro-001",
  "user_id": 42,
  "taken_at_ms": 1714900000000,
  "tick_index": 192123,
  "preseed_version": "v2.5.0",
  "config_hash": "sha256:..." ,
  "metrics": {
    "tier_max_seen": 3,
    "active_for_tier": {"0": 712, "1": 84, "2": 19, "3": 5},
    "ebm_wells_count": 27,
    "ebm_wells_dormant": 6,
    "kg_nodes": 1834,
    "kg_edges": 9214
  },
  "files": [
    {
      "path": "state/lnn.npz",
      "bytes": 1234567,
      "sha256": "..."
    }
  ],
  "encryption": {
    "scheme": "xchacha20-poly1305",
    "wrapped_dek_b64": "...",
    "kek_id": "kek-2026-05"
  },
  "signature": {
    "alg": "ecdsa-p256-sha256",
    "engine_cert_thumbprint": "sha256:...",
    "sig_b64": "..."
  }
}
```

### 2.2 Pflichtfelder

* `snapshot_id`, `format_version`, `engine_id`, `user_id`,
  `taken_at_ms`, `files[]` (mit `path`, `bytes`, `sha256`).
* `signature.engine_cert_thumbprint` und `signature.sig_b64`
  (Pflicht ab M5.6 — bis dahin Engine im Test-Mode mit Dummy-Signatur).

### 2.3 Optional

* `preseed_version`, `config_hash`, `metrics`, `encryption`.

---

## 3. Inhalts-Layout pro Domäne

```
manifest.json
state/
  lnn.npz                # NumPy-NPZ: hidden state, weights, tau-table
  ebm.npz                # NumPy-NPZ: theta_history, well_states
  kg/
    nodes.parquet
    edges.parquet
    wells.parquet
  tier/
    active_for_tier.parquet
  seed/
    preseed_version.txt
    preseed_overrides.json     # nutzer­spezifische Overrides
  random/
    rng_state.json             # numpy RNG Bit-Generator state
checks/
  sha256.txt                   # eine Zeile pro Datei
  format_version.txt           # 'v1.0.0'
  build_id.txt                 # Engine-Wheel-Build-Hash
```

**`nodes.parquet`** (KG-Knoten):

| Spalte           | Typ      | Notiz |
|------------------|----------|-------|
| `node_id`        | int64    | dichte ID |
| `word`           | string   |  |
| `lang`           | string   |  |
| `tier`           | int8     | 0..N |
| `created_tick`   | int64    | Tick-Index der Geburt |
| `last_seen_tick` | int64    | Tick-Index der letzten Aktivität |
| `seen_count`     | int64    |  |
| `embedding`      | binary   | NumPy-Vektor, packed |

**`edges.parquet`** (KG-Kanten):

| Spalte        | Typ    | Notiz |
|---------------|--------|-------|
| `src`         | int64  |  |
| `dst`         | int64  |  |
| `weight`      | float32| 0..1 |
| `created_tick`| int64  |  |
| `decay_index` | int32  | für synaptic-pruning-Phase |

**`wells.parquet`** (EBM-Wells):

| Spalte           | Typ              | Notiz |
|------------------|------------------|-------|
| `well_id`        | int64            |  |
| `members`        | list<int64>      | gefroren bei Geburt |
| `tier`           | int8             |  |
| `birth_tick`     | int64            |  |
| `dormant`        | bool             |  |
| `theta_at_birth` | float32          |  |

---

## 4. Upload-Sequenz

```
Engine                         Hub                          R2

|—— WS frame "engine/snapshot/start" ——▶|
|     {snapshot_id, bytes, sha256_total} |
|                                        |
|◀—— WS frame "server/snapshot/ack" ——|
|     {ok: true, upload_token}           |
|                                        |
|—— HTTP PUT /snapshots/raw ————————————▶|
|     binary tar.zst (chunked)           |—— PUT object key ——▶|
|                                        |◀—— ETag ————————————|
|◀—— HTTP 200 {sha256_verified} ——————|
|                                        |
|—— WS frame "engine/snapshot/finalize" ▶|
|◀—— WS frame "server/snapshot/done" ——|
|     {snapshot_id, is_active: true}     |
```

* `PUT /snapshots/raw` ist der einzige Endpoint, der Bytes >1 MiB
  akzeptiert; Caddy-Limits sind entsprechend gesetzt (siehe `M0.4`).
* Authentifizierung: Bearer + Engine-Client-Cert (über Cloudflare-
  Header, validiert).
* Idempotenz: Wenn Hub bereits `snapshot_id` mit identischem
  `sha256_total` kennt → `200 OK, is_active=true` ohne Re-Upload.

---

## 5. Verifikation server­seitig

Schritte (in dieser Reihenfolge):

1. **Header-Check** — Content-Length passt zu `bytes` aus `start`.
2. **SHA-256-Stream** — Hub berechnet `sha256` während des
   PUT-Empfangs; Abgleich gegen `start.sha256_total`. Mismatch →
   `400 sha_mismatch`, kein R2-PUT.
3. **R2-PUT** — Object hochladen; ETag prüfen.
4. **Tar-Index** — Hub entpackt nur `manifest.json` (streamend, max
   1 MiB) und validiert gegen JSON-Schema (`v1.0.0`).
5. **Engine-Signatur** — `manifest.signature.sig_b64` gegen
   `engine_cert_thumbprint` prüfen (Cert-Lookup in
   `engine_registrations`).
6. **Hash-Konsistenz** — `manifest.files[].sha256` muss zu
   `checks/sha256.txt` passen (zweiter, redundanter Pass —
   kein voller Entpack-Test in v1.0; in v2.0 voller Pass).
7. **Quota-Check** — `quota_usage('snapshot.bytes_30d')` updaten;
   bei Überschreitung `409 quota_exceeded` und R2-Cleanup.
8. **Active-Flag** — `snapshots.is_active = 1` setzen.

Alle Schritte werden im Audit-Log protokolliert (`action=snapshot.upload`,
`target_id=snapshot_id`).

---

## 6. Verschlüsselung

### 6.1 Klartext-Modus (v1.0 Default)

* Keine clientseitige Verschlüsselung des Inhalts.
* R2 SSE-S3 deckt at-rest-Schutz minimal ab.
* `manifest.encryption.scheme` = `"none"`.

### 6.2 Envelope-Modus (Empfohlen, ab v0.5.x verpflichtend)

* Engine generiert pro Snapshot ein DEK (32 B random).
* Inhalts­dateien (`state/*`) werden mit XChaCha20-Poly1305 (AEAD)
  verschlüsselt; `tar.zst` enthält die verschlüsselten Bytes.
* DEK wird mit KEK (Master-Key, gespeichert in SOPS) gewrappt;
  Resultat in `manifest.encryption.wrapped_dek_b64`.
* `kek_id` referenziert den aktuellen KEK; Rotation siehe
  `architecture/security.md` §8.

### 6.3 Restore mit Verschlüsselung

* Hub stellt Snapshot über signed-URL bereit; **Engine**
  entschlüsselt mit KEK (Engine besitzt KEK-Lese-Recht via SOPS-
  Empfänger; Hub besitzt es **nicht**, sieht nur `wrapped_dek`).
* Damit: Hub hat keinen Zugriff auf Snapshot-Inhalt → Confidentiality-
  Schutz auch gegen Hub-Kompromittierung.

> *Limit v1.0.* In v1.0 hat der Hub den KEK (sonst würde `r2-pull` auf
> Vault nichts validieren können). Echter Engine-only-Modus erst in
> v2.0 mit Hardware-KMS.

---

## 7. Restore-Sequenz

```
Engine                            Hub                           R2

|—— HTTP GET /api/v1/snapshots ——▶|
|◀—— [{snapshot_id, taken_at_ms, …}] ——|
|—— HTTP GET /api/v1/snapshots/<id>/url ▶|
|◀—— signed_url (R2 presigned) ——|
|—— HTTP GET signed_url ————————————————————▶|
|◀—— binary tar.zst —————————————————————————|
|—— local: verify signature, decrypt, untar |
|—— Engine resumes from snapshot.tick_index|
|—— WS "engine/hello" with snapshot_id    ▶|
|◀—— WS "server/welcome" {accepted: true}  |
```

* Engine sendet **nach** lokaler Wiederherstellung sofort einen
  Hello-Frame mit `restore_from_snapshot_id`.
* Hub ergänzt das Audit-Log (`action=engine.restore`).
* Replay-Events vor `taken_at_ms` werden vom Engine **nicht** erneut
  emittiert; Replay-Page bleibt konsistent.

---

## 8. Format-Versionierung

* SemVer für `format_version`: `vMAJOR.MINOR.PATCH`.
* **MAJOR-Bump**: bricht alte Engines (Hub akzeptiert nur Liste
  bekannter Versionen).
* **MINOR-Bump**: additive Felder, alte Hub-Lese-Pfade müssen
  unbekannte Felder ignorieren.
* **PATCH-Bump**: Bug-Fixes, keine Schema-Änderung.

* Hub akzeptiert Liste in `config/snapshot_versions_supported.json`,
  Default `["v1.0.0"]`; M8.1 erweitert sie für v2-Übergang.

---

## 9. Fehlermodi & Recovery

| Fehler                            | Engine-Reaktion              | Hub-Reaktion |
|-----------------------------------|------------------------------|--------------|
| Upload abgebrochen (Netz)         | Retry mit gleicher `snapshot_id` | idempotent: gleicher Hash → ack |
| `400 sha_mismatch`                | Snapshot lokal verwerfen, neuer Versuch nach 30 s | R2-Cleanup |
| `409 quota_exceeded`              | Engine pausiert Auto-Snapshot 24 h | keine R2-Inhalte |
| `signature_invalid`               | Engine-Cert prüfen, ggf. neu enrollen | Audit-Eintrag, kein active |
| `manifest_schema_invalid`         | Engine bricht ab, Bug-Report | Audit, kein active |
| `R2 5xx`                          | Hub Retry (3×, exp.backoff) | bei Endgültig-Fail: ack reverten |

---

## 10. Beispiele

### 10.1 Minimaler Snapshot (Engine kalt, Tier 0 only)

```json
{
  "snapshot_id": "snap_1714900000000_xyz789",
  "format_version": "v1.0.0",
  "engine_id": "raspi-test-001",
  "user_id": 7,
  "taken_at_ms": 1714900000000,
  "tick_index": 0,
  "preseed_version": "v2.5.0",
  "metrics": {"tier_max_seen": 0, "active_for_tier": {"0": 0}, "ebm_wells_count": 0, "kg_nodes": 0, "kg_edges": 0},
  "files": [
    {"path": "state/lnn.npz", "bytes": 65536, "sha256": "..."},
    {"path": "state/ebm.npz", "bytes": 4096,  "sha256": "..."},
    {"path": "state/kg/nodes.parquet", "bytes": 1024, "sha256": "..."},
    {"path": "state/kg/edges.parquet", "bytes": 1024, "sha256": "..."},
    {"path": "state/random/rng_state.json", "bytes": 256, "sha256": "..."}
  ]
}
```

### 10.2 Reifer Snapshot (Tier 3, viele Wells)

```json
{
  "snapshot_id": "snap_1714900000000_abc123",
  "format_version": "v1.0.0",
  "engine_id": "macbook-pro-001",
  "user_id": 42,
  "taken_at_ms": 1714900000000,
  "tick_index": 192123,
  "metrics": {
    "tier_max_seen": 3,
    "active_for_tier": {"0": 712, "1": 84, "2": 19, "3": 5},
    "ebm_wells_count": 27,
    "ebm_wells_dormant": 6,
    "kg_nodes": 1834,
    "kg_edges": 9214
  },
  "files": [
    {"path": "state/lnn.npz", "bytes": 1234567, "sha256": "..."},
    {"path": "state/ebm.npz", "bytes": 56789,    "sha256": "..."},
    {"path": "state/kg/nodes.parquet", "bytes": 89012, "sha256": "..."},
    {"path": "state/kg/edges.parquet", "bytes": 234567,"sha256": "..."},
    {"path": "state/kg/wells.parquet", "bytes": 12345, "sha256": "..."},
    {"path": "state/tier/active_for_tier.parquet", "bytes": 4567, "sha256": "..."},
    {"path": "state/random/rng_state.json", "bytes": 256, "sha256": "..."}
  ]
}
```

---

*Stand: 2026-05-08 · Greenfield-Initial · eingefroren ab v0.3.x ·
referenziert aus M2, M3, M5, M8.*
