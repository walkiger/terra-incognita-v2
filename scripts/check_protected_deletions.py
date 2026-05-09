#!/usr/bin/env python3
"""Block silent deletions of protected paths.

Runs in two modes:

- **Local** (pre-commit hook): inspects staged deletions
  (``git diff --cached --diff-filter=D --name-only``) and the in-progress
  commit message file at ``$PRE_COMMIT_COMMIT_MSG_FILE`` (or
  ``.git/COMMIT_EDITMSG``).

- **CI** (GitHub Actions): inspects deletions across the full PR diff
  (``git diff origin/<base>...HEAD --diff-filter=D --name-only``) and reads
  approvals from the PR-level spec at ``.agent-os/pr-spec.json`` plus the
  combined log of every commit body in the PR range.

Exit codes:

- ``0``  — no protected deletions, or all approved.
- ``1``  — at least one unapproved protected deletion.
- ``2``  — internal error (e.g. git invocation failed).

Approval channels (any one is sufficient):

1. A line ``approved_deletions: <path1> <path2> …`` in any commit body
   that introduces the deletion (local pre-commit reads only the current
   message; CI scans the full PR range).
2. A list ``approved_deletions: ["docs/foo.md", ...]`` in
   ``.agent-os/pr-spec.json``.

See ``.cursor/rules/NO-SILENT-DELETIONS.mdc`` for the rule contract.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

# --- Protected path policy --------------------------------------------------

PROTECTED_PREFIXES: tuple[str, ...] = (
    "docs/",
    "knowledge/",
    "reference/",
    "memory/",
    "archive/legacy-docs/",
    "archive/legacy-terra/tests/",
    ".github/workflows/",
    ".cursor/rules/",
    ".cursor/agents/",
)

PROTECTED_EXACT: frozenset[str] = frozenset(
    {
        "CLAUDE.md",
        "Anweisungen.md",
        "catchup.md",
        "README.md",
        "archive/legacy-docs/Implementierungen.Architektur.md",
    }
)

PROTECTED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^archive/legacy-docs/Implementierung\..+\.md$"),
)

# Carve-outs: paths that match these never count as protected even if they
# happen to live under a protected prefix.
CARVE_OUT_FRAGMENTS: tuple[str, ...] = (
    "/__pycache__/",
    "/.pytest_cache/",
    "/node_modules/",
    "/dist/",
    "/build/",
)

APPROVAL_LINE_RE = re.compile(r"^approved_deletions:\s*(.+)$", re.MULTILINE)
SPEC_PATH = Path(".agent-os/pr-spec.json")


# --- helpers ---------------------------------------------------------------


def _run(cmd: list[str]) -> str:
    """Run a git command and return stdout. Exit 2 on failure."""
    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True, encoding="utf-8"
        )
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(
            f"check_protected_deletions: git failed: {' '.join(cmd)}\n"
            f"{exc.stderr}\n"
        )
        sys.exit(2)
    return result.stdout


def is_protected(path: str) -> bool:
    if any(frag in f"/{path}" for frag in CARVE_OUT_FRAGMENTS):
        return False
    if path in PROTECTED_EXACT:
        return True
    if any(path.startswith(prefix) for prefix in PROTECTED_PREFIXES):
        return True
    if any(pat.match(path) for pat in PROTECTED_PATTERNS):
        return True
    return False


def _parse_approval_block(text: str) -> set[str]:
    """Extract whitespace/comma-separated paths from approved_deletions lines."""
    found: set[str] = set()
    for raw in APPROVAL_LINE_RE.findall(text or ""):
        for token in re.split(r"[\s,]+", raw.strip()):
            token = token.strip().strip('"').strip("'")
            if token:
                found.add(token)
    return found


def _approvals_from_commit_msg() -> set[str]:
    msg_path = os.environ.get("PRE_COMMIT_COMMIT_MSG_FILE")
    if not msg_path:
        msg_path = ".git/COMMIT_EDITMSG"
    p = Path(msg_path)
    if not p.exists():
        return set()
    return _parse_approval_block(p.read_text(encoding="utf-8", errors="replace"))


def _approvals_from_spec() -> set[str]:
    if not SPEC_PATH.exists():
        return set()
    try:
        data = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(
            f"check_protected_deletions: cannot read {SPEC_PATH}: {exc}\n"
        )
        return set()
    items = data.get("approved_deletions") or []
    return {str(x).strip() for x in items if str(x).strip()}


def _is_ci() -> bool:
    return os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _ci_base_ref() -> str:
    raw = (os.environ.get("GITHUB_BASE_REF") or "main").strip()
    if raw.startswith("refs/heads/"):
        raw = raw[len("refs/heads/") :]
    return raw or "main"


def _ci_deletions(base: str) -> list[str]:
    out = _run(
        [
            "git",
            "diff",
            f"origin/{base}...HEAD",
            "--diff-filter=D",
            "--name-only",
        ]
    )
    return [line for line in out.splitlines() if line.strip()]


def _ci_approvals(base: str) -> set[str]:
    log = _run(
        ["git", "log", f"origin/{base}..HEAD", "--no-merges", "--format=%B%n--END--"]
    )
    return _parse_approval_block(log)


def _local_deletions() -> list[str]:
    out = _run(
        ["git", "diff", "--cached", "--diff-filter=D", "--name-only"]
    )
    return [line for line in out.splitlines() if line.strip()]


def _matches_approval(path: str, approved: Iterable[str]) -> bool:
    for entry in approved:
        if not entry:
            continue
        if path == entry:
            return True
        if entry.endswith("/") and path.startswith(entry):
            return True
    return False


# --- main ------------------------------------------------------------------


def main() -> int:
    ci = _is_ci()

    if ci:
        base = _ci_base_ref()
        deletions = _ci_deletions(base)
        approvals = _approvals_from_spec() | _ci_approvals(base)
        mode_label = f"CI (origin/{base}...HEAD)"
    else:
        deletions = _local_deletions()
        approvals = _approvals_from_spec() | _approvals_from_commit_msg()
        mode_label = "local (staged)"

    if not deletions:
        return 0

    protected = [p for p in deletions if is_protected(p)]
    if not protected:
        return 0

    blocked = [p for p in protected if not _matches_approval(p, approvals)]
    if not blocked:
        print(
            "check_protected_deletions: all protected deletions approved "
            f"({mode_label})."
        )
        for p in protected:
            print(f"  approved: {p}")
        return 0

    sys.stderr.write(
        "ERROR: silent deletion of protected paths "
        f"({mode_label}).\n\nBlocked deletions:\n"
    )
    for p in blocked:
        sys.stderr.write(f"  - {p}\n")
    sys.stderr.write(
        "\nApproval channels (any one is sufficient):\n"
        "  1. Add 'approved_deletions: <path1> <path2>' to a commit body in this PR.\n"
        "  2. List the paths in '.agent-os/pr-spec.json' under 'approved_deletions'.\n"
        "\nSee .cursor/rules/NO-SILENT-DELETIONS.mdc for the full policy.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
