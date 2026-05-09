import argparse
import datetime as dt
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / ".agent-os" / "self-heal"
MEM_OPEN = ROOT / "memory" / "runtime" / "open-issues.md"
MEM_BUGS = ROOT / "memory" / "runtime" / "known-bugs.md"
MEM_SYSTEMIC = ROOT / "memory" / "runtime" / "systemic-issues.md"


def infer_pattern(ci_result: str) -> tuple[str, str, str]:
    result = (ci_result or "").upper()
    if "SECURITY" in result:
        return (
            "Repeated security validation gaps",
            "Inconsistent validation enforcement across layers",
            "High risk of exploitability and policy drift",
        )
    if "AUDIT" in result:
        return (
            "Recurring architecture violations",
            "Separation-of-concerns boundaries are not consistently enforced",
            "Medium-high risk of long-term maintainability degradation",
        )
    if "TEST" in result or "CI_FAIL" in result:
        return (
            "Repeated contract/test instability",
            "Missing shared validation and contract hardening",
            "High instability in API/UI integration behavior",
        )
    return (
        "General recurring CI failure",
        "Cross-layer governance drift",
        "Medium systemic instability risk",
    )


def build_report(ci_result: str, pr: str) -> str:
    pattern, cause, impact = infer_pattern(ci_result)
    ts = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    issue_slug = pattern.lower().replace(" ", "-").replace("/", "-")[:60]

    return f"""## SELF-HEALING FIX PROPOSAL

Timestamp: {ts}
PR: {pr}
CI Result: {ci_result}

### ISSUE
{pattern}

### ROOT CAUSE
{cause}

### PROPOSED FIX
1. Consolidate failing rule boundaries into one shared contract policy layer.
2. Remove duplicated cross-layer logic causing repeated drift.
3. Add targeted regression checks for the detected failure family.
4. Update memory runtime/system entries for recurrence tracking.
5. Request orchestrator approval for implementation plan.

### IMPACT
- improved stability
- reduced future failures

### PROPOSED BRANCH
fix/self-heal/{issue_slug}
"""


def append_memory(report: str) -> None:
    MEM_SYSTEMIC.parent.mkdir(parents=True, exist_ok=True)
    if not MEM_SYSTEMIC.exists():
        MEM_SYSTEMIC.write_text("# Systemic Issues Memory\n", encoding="utf-8")
    with MEM_SYSTEMIC.open("a", encoding="utf-8") as f:
        f.write("\n\n---\n")
        f.write(report)

    for path in (MEM_OPEN, MEM_BUGS):
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(f"# {path.stem.replace('-', ' ').title()}\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate self-healing proposal artifacts.")
    parser.add_argument("--ci-result", required=True)
    parser.add_argument("--pr", default="")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report(args.ci_result, args.pr)
    md = OUT_DIR / "latest-proposal.md"
    meta = OUT_DIR / "latest-proposal.json"

    md.write_text(report, encoding="utf-8")
    meta.write_text(json.dumps({"ci_result": args.ci_result, "pr": args.pr}, indent=2), encoding="utf-8")
    append_memory(report)

    print(str(md))


if __name__ == "__main__":
    main()
