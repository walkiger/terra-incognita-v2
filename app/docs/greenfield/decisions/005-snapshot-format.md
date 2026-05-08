# ADR-005 — Snapshot-Format `tar.zst` mit `manifest.json`-First

* **Status:** Accepted
* **Datum:** 2026-05-08
* **Bezug:** `protocols/snapshot.md`,
  `architecture/data-model.md` §6.

## Context

Engine-State umfasst LNN-Hidden-State, EBM-Wells, KG-Knoten/Kanten,
Tier-Tabellen, RNG-State. Diese Daten sind heterogen (NPZ, Parquet,
JSON, Binary) und ihr Volumen wächst mit Tier-Reife (vereinzelt
> 100 MiB).

Anforderungen:

* Streamable (Hub kann Manifest lesen, bevor alle Bytes da sind).
* Effiziente Kompression (Zstd > gzip in Geschwindigkeit + Ratio).
* Plattform-neutral (Engine läuft auf Mac/Linux/Windows).
* Format-Versionierbar.
* Optional verschlüsselbar (AEAD pro Datei).

## Decision

Container ist `tar.zst` mit folgendem Layout (siehe
`protocols/snapshot.md` §3):

```
manifest.json                # erste Datei, immer
state/lnn.npz
state/ebm.npz
state/kg/{nodes,edges,wells}.parquet
state/tier/active_for_tier.parquet
state/seed/{preseed_version.txt, preseed_overrides.json}
state/random/rng_state.json
checks/{sha256.txt, format_version.txt, build_id.txt}
```

`manifest.json` ist **immer** die erste Datei im Tar-Stream, sodass
ein Streaming-Reader binnen weniger KiB die kompletten Metadaten
extrahieren kann (`bytes`, `sha256` pro Datei, `format_version`).

Format-Versionierung folgt SemVer (`v1.0.0`), Hub akzeptiert eine
Whitelist (`config/snapshot_versions_supported.json`).

## Consequences

* **Positiv:**
  * Standard-Werkzeuge (`tar`, `zstd`) reichen für Inspektion.
  * Hub-Verifikation kann früh (auf Manifest-Ebene) abbrechen, bevor
    große Files weiter geladen werden.
  * Versionierung sauber: Hub kann z.B. `v1.0.0` und `v1.1.0`
    parallel akzeptieren, wenn additive Felder.
* **Negativ:**
  * Tar-Streaming-Reader auf Server muss korrekt mit großem
    Content-Length-Header umgehen (Caddy-Limits in M0.4 beachtet).
* **Neutral:**
  * AEAD-Verschlüsselung ist optional; in v0.5.x verpflichtend.

## Alternatives Considered

* **HDF5-Container**: alternative scientific format, aber kein
  Standard-Werkzeug auf Servern; Streaming weniger einfach.
* **Pickle-Stream**: nicht akzeptabel (Sicherheits-Risiko bei
  Deserialisierung).
* **Multipart-Upload mit getrennten Dateien**: mehrere R2-Objekte,
  schwer atomar zu finalisieren.

## References

* `protocols/snapshot.md`
* `architecture/data-model.md` §6
* `M3-local-engine-skeleton.md` (Snapshot-CLI)

---

*Greenfield-Initial-ADR.*
