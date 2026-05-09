# extracted/

One directory per **`document_id`**:

**Binaries:** `source.pdf` wird **nicht** ins Git aufgenommen (`.gitignore`). Für Reprod Ingest aus `research/incoming/` oder Legacy-Spiegel siehe [`research/README.md`](../README.md).

```
extracted/<document_id>/manifest.json       # required — tracks L0–L4
extracted/<document_id>/l1_raw_text.json   # after L1
…
```

Initial population steps when a new PDF lands:

1. Create `extracted/<document_id>/` matching the incoming PDF basename rule.
2. Write `manifest.json` with all layers `pending` except **L0** → `complete` once registered.
3. Advance layers sequentially in the manifest as artifacts appear.
