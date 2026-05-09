import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC_FILE = ROOT / ".agent-os" / "pr-spec.json"
META_STATE_FILE = ROOT / ".agent-os" / "meta-state.json"
DECISIONS_FILE = ROOT / "memory" / "system" / "decisions.md"
ARCH_FILE = ROOT / "memory" / "system" / "architecture.md"


def load_json(path: pathlib.Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def evaluate() -> tuple[str, str, list[str], str]:
    issues: list[str] = []
    risk = "LOW"
    permission = "ALLOW"
    status = "VALID"

    spec = load_json(SPEC_FILE)
    meta_state = load_json(META_STATE_FILE)
    ci_fail_cycles = int(meta_state.get("ci_fail_cycles", 0))
    architecture_change = bool(meta_state.get("architecture_change_detected", False))
    multi_agent_conflict = bool(meta_state.get("multi_agent_conflict", False))

    if not SPEC_FILE.exists():
        issues.append("missing orchestrator spec file")
        permission = "BLOCKED"
        risk = "HIGH"
        status = "INVALID"

    if architecture_change and not DECISIONS_FILE.exists():
        issues.append("architecture change flagged without decisions memory file")
        permission = "BLOCKED"
        risk = "HIGH"
        status = "INVALID"

    if ci_fail_cycles >= 3:
        issues.append("3+ CI fail cycles detected")
        permission = "BLOCKED"
        risk = "HIGH"
        status = "DEGRADED"

    if multi_agent_conflict:
        issues.append("multi-agent conflict detected")
        if permission != "BLOCKED":
            permission = "GUARDED"
            risk = "MEDIUM"
            status = "DEGRADED"

    if spec.get("agents") and "frontend" in spec["agents"] and "backend" not in spec["agents"]:
        # Heuristic for likely architecture drift in full-stack changes.
        issues.append("frontend assigned without backend context; verify contract alignment")
        if permission == "ALLOW":
            permission = "GUARDED"
            risk = "MEDIUM"
            status = "DEGRADED"

    if not ARCH_FILE.exists():
        issues.append("missing architecture memory file")
        if permission == "ALLOW":
            permission = "GUARDED"
            risk = "MEDIUM"
            status = "DEGRADED"

    decision = {
        "ALLOW": "Execution permitted.",
        "GUARDED": "Execution permitted with governance warnings.",
        "BLOCKED": "Execution blocked pending governance remediation.",
    }[permission]

    return permission, status, issues, risk, decision


def main() -> None:
    permission, status, issues, risk, decision = evaluate()

    print("## ORCHESTRATOR VALIDATION")
    print(f"STATUS: {status}")
    print("ISSUES:")
    if issues:
        for issue in issues:
            print(f"- {issue}")
    else:
        print("- none")
    print(f"RISK LEVEL: {risk}")
    print(f"EXECUTION PERMISSION: {permission}")
    print(f"DECISION: {decision}")

    if permission == "BLOCKED":
        sys.exit(1)


if __name__ == "__main__":
    main()
