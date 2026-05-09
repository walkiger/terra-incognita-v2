#!/usr/bin/env python3
"""Rewrite current branch's commits after <base> using cherry-pick -n, stripping
Cursor agent Co-authored-by trailers from each original message.

Usage (from repo root):
  py scripts/rewrite_branch_strip_cursor_coauthor.py aafac4c

After a successful run, the current branch points at the rewritten tip (same
tree sequence as before, new commit hashes). Force-push if the branch was
already published.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = str(ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from strip_cursor_coauthor_trailer import strip_trailer


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("base", help="First parent to exclude (e.g. merge-base commit)")
    args = ap.parse_args()
    base = args.base

    cur = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if cur == "HEAD":
        print("error: detached HEAD; checkout your feature branch first", file=sys.stderr)
        raise SystemExit(2)

    rev_list = _git("rev-list", "--reverse", f"{base}..HEAD").stdout.strip()
    commits = [c for c in rev_list.splitlines() if c]
    if not commits:
        print("nothing to rewrite", file=sys.stderr)
        raise SystemExit(0)

    _git("checkout", "-B", "_rewrite_strip_coauthor", base)

    msg_path = ROOT / ".git" / "_COMMIT_MSG_REWRITE.tmp"
    try:
        for oid in commits:
            _git("cherry-pick", "-n", oid)
            raw = _git("show", "-s", "--format=%B", oid).stdout
            stripped = strip_trailer(raw)
            msg_path.write_text(stripped, encoding="utf-8", newline="\n")
            subprocess.run(["git", "commit", "-F", str(msg_path)], cwd=ROOT, check=True)
        _git("branch", "-f", cur, "HEAD")
        _git("checkout", cur)
        _git("branch", "-D", "_rewrite_strip_coauthor")
    finally:
        if msg_path.exists():
            msg_path.unlink(missing_ok=True)

    print(f"Rewrote {len(commits)} commit(s) on {cur}; messages stripped of Cursor co-author trailers.")


if __name__ == "__main__":
    main()
