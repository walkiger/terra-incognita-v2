#!/usr/bin/env python3
"""Schema lint (M0.7) — validate committed JSON Schema files parse as JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "research" / "schema"


def main() -> int:
    if not SCHEMA_DIR.is_dir():
        print(f"schema_lint: skip — missing {SCHEMA_DIR.relative_to(ROOT)}")
        return 0
    errors = 0
    for path in sorted(SCHEMA_DIR.glob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"schema_lint: invalid JSON {path.relative_to(ROOT)}: {exc}")
            errors += 1
    if errors:
        return 1
    print(f"schema_lint: OK ({len(list(SCHEMA_DIR.glob('*.json')))} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
