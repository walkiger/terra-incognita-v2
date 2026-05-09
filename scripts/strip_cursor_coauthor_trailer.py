#!/usr/bin/env python3
"""Remove Cursor agent Co-authored-by trailer from a commit message.

Used by:
- pre-commit prepare-commit-msg (see .pre-commit-config.yaml) so agent-driven
  commits stay clean after `pre-commit install --hook-type prepare-commit-msg`.
- optional: git filter-branch --msg-filter "py scripts/strip_cursor_coauthor_trailer.py --stdin"

Not a substitute for disabling Cursor Agent > Attribution — but blocks the
trailer for contributors who install the extra hook type.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _is_cursor_agent_coauthor(line: str) -> bool:
    t = line.strip()
    if not t.lower().startswith("co-authored-by:"):
        return False
    return "cursoragent@cursor.com" in t.lower()


def strip_trailer(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if _is_cursor_agent_coauthor(line):
            continue
        lines.append(line)
    while lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--stdin",
        action="store_true",
        help="Read message from stdin, write stripped message to stdout (for msg-filter).",
    )
    ap.add_argument(
        "path",
        nargs="?",
        help="COMMIT_EDITMSG path (prepare-commit-msg). In-place rewrite.",
    )
    args = ap.parse_args()

    if args.stdin:
        out = strip_trailer(sys.stdin.read())
        sys.stdout.write(out)
        return

    if not args.path:
        ap.error("provide a file path or use --stdin")
    path = Path(args.path)
    raw = path.read_text(encoding="utf-8")
    out = strip_trailer(raw)
    if out != raw:
        path.write_text(out, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
