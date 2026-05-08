"""M0.1 — repo layout and Makefile targets (Greenfield skeleton)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRS = (
    REPO_ROOT / "deploy" / "compose",
    REPO_ROOT / "deploy" / "ansible",
    REPO_ROOT / "secrets",
    REPO_ROOT / "app" / "backend",
    REPO_ROOT / "app" / "engine",
    REPO_ROOT / "app" / "web",
    REPO_ROOT / "app" / "packages",
    REPO_ROOT / "tests",
)

MAKEFILE_TARGETS = (
    "bootstrap",
    "test",
    "fmt",
    "lint",
    "compose-hub",
    "compose-vault",
)


def test_required_directories_exist() -> None:
    for path in REQUIRED_DIRS:
        assert path.is_dir(), f"expected directory: {path.relative_to(REPO_ROOT)}"


def test_makefile_targets_present() -> None:
    makefile = REPO_ROOT / "Makefile"
    assert makefile.is_file(), "Makefile missing"
    text = makefile.read_text(encoding="utf-8")
    for target in MAKEFILE_TARGETS:
        assert target in text, f"Makefile should mention target {target!r}"
