# knowledge/ — Preseed (EN-first KB)

| Datei | Zweck |
|--------|--------|
| **`preseed_v2.json`** | Kanonische Preseed-Knowledge-Base (Wellen `w00_*` … `w12_*`, Mehrsprachigkeit, `_meta` / `_status`). |
| **`verify.py`** | Qualitäts‑ / Schema‑ / Parity‑Checks; **schreibt die gewählte Preseed-Datei zurück** (`_status`, `_meta.stats`, `external_refs`). |

## Nutzung

```text
py knowledge/verify.py --preseed knowledge/preseed_v2.json --quiet
```

(Nur Standardbibliothek — kein zusätzliches `pip install` nötig.)

**Hinweis:** Vor einem Verify-Lauf bei bearbeiteter Datei **Backup** ziehen oder mit Kopie arbeiten — das Tool aktualisiert absichtlich `_status` und Statistikfelder.

## Herkunft / Legacy

Enrichment-Pipelines und Fetch-Logik leben im Legacy-Repo **`walkiger/terra-incognita`** (nicht hier aufgebaut). Dieses Verzeichnis hält den **Datensnapshot** für das Greenfield-Produkt nachziehbar bereit.
