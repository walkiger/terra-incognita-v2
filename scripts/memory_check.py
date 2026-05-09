import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
MEMORY = ROOT / "memory"

REQUIRED_FILES = [
    MEMORY / "system" / "architecture.md",
    MEMORY / "system" / "decisions.md",
    MEMORY / "system" / "constraints.md",
    MEMORY / "runtime" / "open-issues.md",
    MEMORY / "runtime" / "known-bugs.md",
]


def gather_changed_files() -> list[str]:
    head = (ROOT / ".agent-os" / "pr-spec.json")
    # Best-effort signal from current branch state in CI clone.
    # If unavailable, return empty and only run structural checks.
    return [str(head.relative_to(ROOT))] if head.exists() else []


def check_decision_timestamps(decisions_text: str) -> list[str]:
    issues = []
    for block in decisions_text.split("## "):
        if block.strip().startswith("Decision:") and "Timestamp:" not in block:
            name = block.splitlines()[0].strip()
            issues.append(f"decision entry missing timestamp: {name}")
    return issues


def check_deprecated_marking(decisions_text: str) -> list[str]:
    # Soft consistency: if deprecated appears, enforce status syntax.
    issues = []
    if "deprecated" in decisions_text.lower() and "Status: deprecated" not in decisions_text:
        issues.append("deprecated decision entries must use 'Status: deprecated'")
    return issues


def main() -> None:
    warnings: list[str] = []

    for req in REQUIRED_FILES:
        if not req.exists():
            warnings.append(f"missing memory file: {req.relative_to(ROOT)}")

    decisions_file = MEMORY / "system" / "decisions.md"
    if decisions_file.exists():
        decisions_text = decisions_file.read_text(encoding="utf-8", errors="ignore")
        warnings.extend(check_decision_timestamps(decisions_text))
        warnings.extend(check_deprecated_marking(decisions_text))

    # API and architecture change heuristics can be tightened later.
    changed = gather_changed_files()
    if changed and "memory/system/decisions.md" not in changed:
        warnings.append("memory warning: ensure architecture/API decisions are reflected when relevant")

    if warnings:
        print("Memory check warnings:")
        for w in warnings:
            print(f"- {w}")
        # Intentionally non-blocking per spec: warning only.
        sys.exit(0)

    print("Memory check passed.")


if __name__ == "__main__":
    main()
