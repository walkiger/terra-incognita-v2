"""
Validate that an open GitHub Pull Request carries at least one agent:* label.

On "Re-run failed jobs", GitHub reuses a frozen ``GITHUB_EVENT_PATH`` snapshot.
The REST API (or authenticated ``gh``) reads **current** labels while the PR
number usually stays valid across reruns.

Resolution order:

1. **HTTP API** when a token plus repository id plus PR number are available.
   ``GITHUB_REPOSITORY`` may be omitted if ``repository.full_name`` (or base repo)
   is present on the event JSON.

2. **GitHub CLI** (`gh api ...`) when no ``GITHUB_TOKEN`` env is set but ``gh``
   is installed and logged in — common for local reruns.

3. **Frozen event** labels from ``pull_request.labels`` — last resort.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


REQUIRED_AGENT_LABELS = {
    "agent:backend",
    "agent:frontend",
    "agent:research",
    "agent:test",
    "agent:security",
    "agent:audit",
    "agent:docs",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    sys.exit(1)


def _event_payload(event_path: str) -> dict[str, Any]:
    with Path(event_path).open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    return raw if isinstance(raw, dict) else {}


def _pr_from_event_path(event_path: str) -> dict[str, Any] | None:
    pr = _event_payload(event_path).get("pull_request")
    return pr if isinstance(pr, dict) else None


def _repository_full_name_from_event(event_path: str) -> str | None:
    """
    ``GITHUB_REPOSITORY`` is often ``owner/repo``. The pull_request webhook
    duplicates this as ``repository.full_name`` (and on ``base.repo``).
    """
    event = _event_payload(event_path)

    repo = event.get("repository")
    if isinstance(repo, dict):
        fn = repo.get("full_name")
        if isinstance(fn, str) and "/" in fn.strip():
            return fn.strip()

    pr = event.get("pull_request")
    if isinstance(pr, dict):
        base = pr.get("base")
        if isinstance(base, dict):
            br = base.get("repo")
            if isinstance(br, dict):
                fn = br.get("full_name")
                if isinstance(fn, str) and "/" in fn.strip():
                    return fn.strip()

    return None


def _labels_from_event_pr(pr: dict[str, Any]) -> set[str]:
    labels = pr.get("labels", [])
    if not isinstance(labels, list):
        return set()
    return {
        str(item.get("name", "")).strip()
        for item in labels
        if isinstance(item, dict) and item.get("name")
    }


def _pr_number_from_env() -> int | None:
    raw = (
        os.getenv("GITHUB_PR_NUMBER")
        or os.getenv("PR_NUMBER")
        or ""
    ).strip()
    return int(raw) if raw.isdigit() else None


def _pr_number_from_event_path(event_path: str) -> int | None:
    pr = _pr_from_event_path(event_path)
    if not pr:
        return None
    num = pr.get("number")
    return int(num) if isinstance(num, int) else None


def _fetch_live_pr_labels(repository: str, pr_number: int, token: str) -> list[str]:
    """
    Issue-scoped Labels API applies to Pull Requests too.
    GET /repos/{owner}/{repo}/issues/{issue_number}/labels
    """
    url = (
        "https://api.github.com/repos/"
        f"{repository}/issues/{pr_number}/labels"
        "?per_page=100"
    )
    request_obj = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request_obj, timeout=30) as response:
            body = response.read().decode()
    except urllib.error.HTTPError as exc:
        fail(f"GitHub API label fetch failed (HTTP {exc.code}): {exc.reason}")

    try:
        parsed: Any = json.loads(body)
    except json.JSONDecodeError as exc:
        fail(f"GitHub API label fetch returned invalid JSON: {exc}")

    if not isinstance(parsed, list):
        fail(f"Unexpected GitHub API label payload shape: {type(parsed).__name__}")

    return [str(obj.get("name", "")).strip() for obj in parsed if obj.get("name")]


def _fetch_labels_via_gh_cli(repository: str, pr_number: int) -> list[str] | None:
    """
    Uses the authenticated ``gh`` host token (no ``GITHUB_TOKEN`` required).
    Returns ``None`` if ``gh`` is missing or the call fails.
    """
    if not shutil.which("gh"):
        return None

    try:
        proc = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repository}/issues/{pr_number}/labels",
            ],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if proc.returncode != 0:
        return None

    try:
        parsed: Any = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, list):
        return None

    return [
        str(obj.get("name", "")).strip()
        for obj in parsed
        if isinstance(obj, dict) and obj.get("name")
    ]


def main() -> None:
    event_path = os.getenv("GITHUB_EVENT_PATH")
    env_repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    token = (os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or "").strip()

    pr_number = _pr_number_from_env()
    if pr_number is None and event_path and Path(event_path).is_file():
        pr_number = _pr_number_from_event_path(event_path)

    repo = env_repo
    if not repo and event_path and Path(event_path).is_file():
        repo = _repository_full_name_from_event(event_path) or ""

    label_source = ""

    names_for_match: list[str]

    if repo and token and pr_number:
        print(f"Fetching current labels for PR #{pr_number} via GitHub API …")
        names_for_match = _fetch_live_pr_labels(repo, pr_number, token)
        label_source = "http_api"

    elif repo and pr_number and shutil.which("gh"):
        gh_names = _fetch_labels_via_gh_cli(repo, pr_number)
        if gh_names is not None:
            print(
                f"Fetched current labels for PR #{pr_number} via `gh api` …",
            )
            names_for_match = gh_names
            label_source = "gh_cli"
        elif not event_path or not Path(event_path).is_file():
            fail(
                "Cannot validate labels: gh CLI fetch failed/misconfigured "
                "and no GITHUB_EVENT_PATH fallback exists.",
            )
        else:
            pr = _pr_from_event_path(event_path)
            if not pr:
                print("No pull_request payload found on event. Skipping label check.")
                return
            names_for_match = list(_labels_from_event_pr(pr))
            label_source = "frozen_event"
            print(
                "gh CLI did not return labels; using frozen GITHUB_EVENT_PATH.",
            )

    else:
        if not event_path or not Path(event_path).is_file():
            fail(
                "Cannot validate PR labels: no API/gh context "
                "(need token or gh + repo id + PR number) and no readable "
                "GITHUB_EVENT_PATH.",
            )

        pr = _pr_from_event_path(event_path)
        if not pr:
            print("No pull_request payload found on event. Skipping label check.")
            return

        names_for_match = list(_labels_from_event_pr(pr))
        label_source = "frozen_event"
        print(
            "Using labels from frozen GITHUB_EVENT_PATH only "
            "(no token, gh unavailable, or repo id missing from env+event).",
        )

    normalized = {n for n in names_for_match if n}
    matched = sorted(normalized.intersection(REQUIRED_AGENT_LABELS))

    if not matched:
        expected = ", ".join(sorted(REQUIRED_AGENT_LABELS))
        extra = ""

        if label_source == "http_api":
            extra = (
                " Labels were read from the live GitHub API — add one of the "
                "required labels on this PR."
            )
        elif label_source == "gh_cli":
            extra = (
                " Labels were read via `gh api` — add one of the required "
                "labels on this PR."
            )
        else:
            extra = (
                "\nNOTE: Stale snapshot only. Prefer CI with token, set "
                "GITHUB_REPOSITORY if needed, or run `gh auth login` for "
                "local `gh api` fallback."
            )

        fail(
            "PR is missing required agent label. "
            f"Add at least one of: {expected}.{extra}")

    print(f"Agent label check passed: {', '.join(matched)}")


if __name__ == "__main__":
    main()
