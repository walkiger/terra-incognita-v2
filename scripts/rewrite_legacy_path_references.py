#!/usr/bin/env python3
"""Rewrite documentation pointers after legacy stack moves into archive/.

Run from repo root after mv:

- Implementierung*.md + Implementierungen.Architektur.md → archive/legacy-docs/
- backend/frontend/tests/docker/requirements/pytest/README → archive/legacy-terra/

This script updates markdown/rule references idempotently (safe to re-run).

Usage:
    py scripts/rewrite_legacy_path_references.py [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
    "build",
}

TEXT_SUFFIXES = {".md", ".mdc", ".yml", ".yaml"}

IMPL_FILE_RE = re.compile(r"(?<![\w/])Implementierung\.([a-z0-9_.]+)\.md")

REL_IMPL_LINK_RE = re.compile(
    r"\(((?:\.\./)+)(Implementierung\.[a-z0-9_.]+\.md)\)"
)
REL_ARCH_LINK_RE = re.compile(
    r"\(((?:\.\./)+)(Implementierungen\.Architektur\.md)\)"
)


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        parts = path.parts
        if any(x in SKIP_DIR_NAMES for x in parts):
            continue
        rel_s = path.relative_to(ROOT).as_posix()
        if rel_s.startswith("archive/legacy-docs/"):
            continue
        if rel_s.startswith("archive/legacy-terra/"):
            continue
        files.append(path)
    return sorted(files)


def rewrite_impl_refs(text: str) -> str:
    text = text.replace(
        "archive/legacy-docs/archive/legacy-docs/",
        "archive/legacy-docs/",
    )
    text = re.sub(
        r"(?<!archive/legacy-docs/)Implementierungen\.Architektur\.md",
        "archive/legacy-docs/Implementierungen.Architektur.md",
        text,
    )

    def _impl_sub(m: re.Match[str]) -> str:
        return f"archive/legacy-docs/Implementierung.{m.group(1)}.md"

    text = IMPL_FILE_RE.sub(_impl_sub, text)

    def _rel_impl(m: re.Match[str]) -> str:
        return f"({m.group(1)}archive/legacy-docs/{m.group(2)})"

    text = REL_IMPL_LINK_RE.sub(_rel_impl, text)

    def _rel_arch(m: re.Match[str]) -> str:
        return f"({m.group(1)}archive/legacy-docs/{m.group(2)})"

    text = REL_ARCH_LINK_RE.sub(_rel_arch, text)
    return text


def rewrite_pytest_paths(text: str, *, apply_test_root_fixes: bool) -> str:
    if apply_test_root_fixes:
        replacements = [
            ("py -m pytest tests/", "py -m pytest archive/legacy-terra/tests/"),
            ("pytest tests/", "pytest archive/legacy-terra/tests/"),
            ("python -m pytest tests/", "python -m pytest archive/legacy-terra/tests/"),
            ("--ignore=tests/", "--ignore=archive/legacy-terra/tests/"),
        ]
        for old, new in replacements:
            text = text.replace(old, new)

    text = text.replace(
        "archive/legacy-terra/archive/legacy-terra/",
        "archive/legacy-terra/",
    )
    return text


def process_file(path: Path, *, dry_run: bool) -> bool:
    raw = path.read_text(encoding="utf-8", errors="replace")
    rel = path.relative_to(ROOT).as_posix()

    apply_tests = not rel.startswith("app/docs/greenfield/")

    updated = rewrite_impl_refs(raw)
    updated = rewrite_pytest_paths(updated, apply_test_root_fixes=apply_tests)

    if updated == raw:
        return False
    if not dry_run:
        path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    changed = 0
    for path in iter_files():
        if process_file(path, dry_run=args.dry_run):
            print(path.relative_to(ROOT))
            changed += 1

    label = "would update" if args.dry_run else "updated"
    print(f"{label} {changed} file(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
