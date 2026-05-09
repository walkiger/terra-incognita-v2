"""YAML lint for Cloudflare tunnel ingress configs (M0.5)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]


def _ingress_rules(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    ing = data.get("ingress")
    assert isinstance(ing, list), f"{path}: ingress must be a list"
    return ing


@pytest.mark.parametrize(
    "relative",
    ["deploy/cloudflared/config.hub.yml", "deploy/cloudflared/config.vault.yml"],
)
def test_config_yaml_parses(relative: str) -> None:
    path = REPO / relative
    assert path.is_file(), path
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert "tunnel" in data
    assert "ingress" in data


def test_no_duplicate_hostnames() -> None:
    seen: set[str] = set()
    dups: list[str] = []
    for rel in ("deploy/cloudflared/config.hub.yml", "deploy/cloudflared/config.vault.yml"):
        path = REPO / rel
        for rule in _ingress_rules(path):
            host = rule.get("hostname")
            if not host:
                continue
            if host in seen:
                dups.append(host)
            seen.add(host)
    assert not dups, f"duplicate hostnames across configs: {dups}"
