import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr.strip()}")
    return result.stdout.strip()


def load_spec(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        spec = json.load(f)
    required = ["feature", "branch", "agents", "acceptance_criteria"]
    missing = [k for k in required if k not in spec]
    if missing:
        raise ValueError(f"Spec missing keys: {', '.join(missing)}")
    return spec


def build_pr_body(spec: dict) -> str:
    agents = ", ".join(spec.get("agents", []))
    criteria = "\n".join(f"- {item}" for item in spec.get("acceptance_criteria", [])) or "- TBD"
    return (
        "## Automated PR from Agent OS\n\n"
        f"### Feature\n{spec['feature']}\n\n"
        f"### Branch\n{spec['branch']}\n\n"
        f"### Agents\n{agents}\n\n"
        "### Acceptance Criteria\n"
        f"{criteria}\n"
    )


def apply_labels(repo: str, pr_number: int, labels: list[str]) -> None:
    if not labels:
        return
    cmd = ["gh", "api", f"repos/{repo}/issues/{pr_number}/labels", "-X", "POST"]
    for label in labels:
        cmd.extend(["-f", f"labels[]={label}"])
    run(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create GitHub PR from orchestrator spec.")
    parser.add_argument("--spec", required=True, help="Path to orchestrator spec JSON file.")
    parser.add_argument("--base", default="main", help="Base branch for PR.")
    parser.add_argument("--head", default="", help="Head branch override.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without creating PR.")
    args = parser.parse_args()

    spec = load_spec(Path(args.spec))
    head_branch = args.head or spec["branch"]
    title = f"Feature: {spec['feature']}"
    body = build_pr_body(spec)

    if args.dry_run:
        print(title)
        print(body)
        return

    run(["git", "checkout", "-B", head_branch])
    run(["git", "push", "-u", "origin", head_branch])
    pr_url = run(["gh", "pr", "create", "--base", args.base, "--head", head_branch, "--title", title, "--body", body])
    print(pr_url)

    repo = os.getenv("GITHUB_REPOSITORY", "")
    if repo and "/" in repo:
        # Optional: best-effort label bootstrap based on agents.
        agent_to_label = {
            "backend": "agent:backend",
            "frontend": "agent:frontend",
            "research": "agent:research",
            "test": "agent:test",
            "security": "agent:security",
            "audit": "agent:audit",
            "docs": "agent:docs",
        }
        labels = sorted({agent_to_label[a] for a in spec.get("agents", []) if a in agent_to_label})
        if labels:
            pr_number = run(["gh", "pr", "view", "--head", head_branch, "--json", "number", "--jq", ".number"])
            apply_labels(repo, int(pr_number), labels)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
