import json
import sys
from pathlib import Path


SPEC_PATH = Path(".agent-os/pr-spec.json")
REQUIRED_KEYS = {"feature", "branch", "agents", "tasks", "acceptance_criteria"}


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    sys.exit(1)


def main() -> None:
    if not SPEC_PATH.exists():
        fail(f"Missing orchestrator spec file: {SPEC_PATH}")

    try:
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON in {SPEC_PATH}: {exc}")

    missing = REQUIRED_KEYS - set(spec.keys())
    if missing:
        fail(f"Orchestrator spec missing keys: {', '.join(sorted(missing))}")

    if not isinstance(spec.get("agents"), list) or not spec["agents"]:
        fail("Orchestrator spec 'agents' must be a non-empty array.")

    if not isinstance(spec.get("tasks"), dict):
        fail("Orchestrator spec 'tasks' must be an object.")

    print(f"Orchestrator spec check passed: {SPEC_PATH}")


if __name__ == "__main__":
    main()
