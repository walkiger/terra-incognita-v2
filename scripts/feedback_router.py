import argparse
import json
import os
import sys


ROUTE_MAP = {
    "TEST_FAIL": "test-agent",
    "SECURITY_FAIL": "security-agent",
    "AUDIT_FAIL": "audit-agent",
    "META_FAIL": "meta",
    "LABEL_FAIL": "orchestrator",
    "CI_FAIL": "orchestrator",
    "PASS": "orchestrator",
}


def infer_failure_type(failed_step_names: list[str], conclusion: str) -> str:
    if conclusion == "success":
        return "PASS"

    lowered = " | ".join(failed_step_names).lower()
    if "frontend test" in lowered or "backend test" in lowered or "run backend tests" in lowered or "run frontend tests" in lowered:
        return "TEST_FAIL"
    if "security" in lowered:
        return "SECURITY_FAIL"
    if "audit" in lowered:
        return "AUDIT_FAIL"
    if "meta-orchestrator" in lowered or "governance" in lowered:
        return "META_FAIL"
    if "label" in lowered:
        return "LABEL_FAIL"
    return "CI_FAIL"


def main() -> None:
    parser = argparse.ArgumentParser(description="Route CI feedback to responsible agent.")
    parser.add_argument("--ci-result", default="", help="Explicit CI result enum.")
    parser.add_argument("--failed-steps", default="[]", help="JSON array of failed step names.")
    parser.add_argument("--conclusion", default="", help="Workflow conclusion from GitHub.")
    parser.add_argument("--pr", default="", help="PR number or URL for output context.")
    args = parser.parse_args()

    if args.ci_result:
        result = args.ci_result
    else:
        try:
            failed_steps = json.loads(args.failed_steps)
        except json.JSONDecodeError:
            failed_steps = []
        result = infer_failure_type(failed_steps, args.conclusion or "failure")

    agent = ROUTE_MAP.get(result, "orchestrator")
    output = {
        "ci_result": result,
        "route_to": agent,
        "pr": args.pr,
    }

    print(json.dumps(output))

    output_file = os.getenv("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"ci_result={result}\n")
            f.write(f"route_to={agent}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
