"""Secrets / SOPS layout (M0.8)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]


def test_sops_config_present() -> None:
    cfg = REPO / "secrets" / ".sops.yaml"
    assert cfg.is_file()
    data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert "creation_rules" in data


def test_no_unencrypted_files_committed() -> None:
    """Reject plaintext secret templates tracked beside encrypted hub secrets."""
    secrets_dir = REPO / "secrets"
    banned = {"hub.plain.yaml", "hub.env"}
    for name in banned:
        assert not (secrets_dir / name).is_file(), (
            f"remove {name} from git — use hub.sops.yaml + decrypt"
        )


def test_hub_sops_has_metadata() -> None:
    raw = (REPO / "secrets" / "hub.sops.yaml").read_text(encoding="utf-8")
    assert "sops:" in raw
    assert "ENC[" in raw
