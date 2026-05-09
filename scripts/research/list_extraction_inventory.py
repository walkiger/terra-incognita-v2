#!/usr/bin/env python3
"""
List all research extraction trees (manifest.json) for batch planning/regeneration.

Outputs JSON (--json) or a human-readable table. Optional validation against
research/schema/manifest.schema.json requires jsonschema (dev dependency).

Usage:
  py scripts/research/list_extraction_inventory.py
  py scripts/research/list_extraction_inventory.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTRACTED = REPO_ROOT / "research" / "extracted"
MANIFEST_SCHEMA = REPO_ROOT / "research" / "schema" / "manifest.schema.json"


def _load_jsonschema_validator():
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return None, None

    schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    return Draft202012Validator(schema), Draft202012Validator


def inventory_rows(*, validate: bool) -> list[dict]:
    validator_cls = None
    validator = None
    if validate:
        validator, validator_cls = _load_jsonschema_validator()
        if validator is None:
            raise RuntimeError(
                "jsonschema is required for --validate (install requirements-dev.txt)"
            )

    rows: list[dict] = []
    if not EXTRACTED.is_dir():
        return rows

    for manifest in sorted(EXTRACTED.glob("*/manifest.json")):
        doc_dir = manifest.parent
        raw = manifest.read_text(encoding="utf-8")
        errors: list[str] = []
        data: dict
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            data = {}
            errors.append(f"json_error:{exc}")

        if validator_cls is not None and data:
            errs = sorted(validator.iter_errors(data), key=lambda e: e.path)
            errors.extend(e.message for e in errs[:8])
            if len(errs) > 8:
                errors.append(f"... and {len(errs) - 8} more schema errors")

        pdf_name = ""
        spi = data.get("source_pdf", "")
        if isinstance(spi, str) and spi:
            pdf_name = Path(spi).name

        incoming_exists = False
        if isinstance(spi, str) and spi.strip():
            pdf_path = REPO_ROOT.joinpath(*spi.replace("\\", "/").split("/"))
            incoming_exists = pdf_path.is_file()

        layers = data.get("layers") if isinstance(data.get("layers"), dict) else {}
        layer_summary: dict[str, str] = {}
        for lk in ("L0", "L1", "L2", "L3", "L4"):
            st = layers.get(lk)
            if isinstance(st, dict):
                layer_summary[lk] = str(st.get("status", "?"))
            else:
                layer_summary[lk] = "missing"

        rows.append(
            {
                "document_id": data.get("document_id", doc_dir.name),
                "manifest_path": str(manifest.relative_to(REPO_ROOT)).replace("\\", "/"),
                "source_pdf": spi,
                "incoming_pdf_basename": pdf_name,
                "incoming_exists": incoming_exists,
                "layers": layer_summary,
                "validation_errors": errors,
            }
        )

    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Inventory research/extracted manifests.")
    ap.add_argument("--json", action="store_true", help="Emit JSON array to stdout.")
    ap.add_argument(
        "--validate",
        action="store_true",
        help="Validate each manifest.json with jsonschema (dev dependency).",
    )
    args = ap.parse_args()

    try:
        rows = inventory_rows(validate=args.validate)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"extracted_roots": rows}, indent=2, ensure_ascii=False))
        return 0

    print(f"# research extraction inventory ({len(rows)} manifests)\n")
    for row in rows:
        layers = ",".join(f"{k}:{v}" for k, v in row["layers"].items())
        vf = "; ".join(row["validation_errors"]) if row["validation_errors"] else ""
        inc = "ok" if row["incoming_exists"] else "MISSING"
        print(f"- {row['document_id']}")
        print(f"    manifest: {row['manifest_path']}")
        print(f"    pdf:      {row.get('incoming_pdf_basename')} [{inc}]")
        print(f"    layers:   {layers}")
        if vf:
            print(f"    schema:   {vf}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
