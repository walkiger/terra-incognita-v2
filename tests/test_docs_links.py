"""Docs link smoke (M0.10)."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_contributing_links_present() -> None:
    text = (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "docs/operations/branch-and-pr-rules.md" in text


def test_readme_pr_pointer_present() -> None:
    text = (REPO / "README.md").read_text(encoding="utf-8")
    assert "docs/operations/branch-and-pr-rules.md" in text
    assert "Vor dem ersten Commit" in text or "branch-and-pr-rules" in text


def test_r2_buckets_doc_present() -> None:
    doc = REPO / "docs" / "operations" / "r2-buckets.md"
    assert doc.is_file()
    body = doc.read_text(encoding="utf-8")
    assert "terra-incognita-prod" in body
    assert "terra-incognita-dev" in body
    assert "litestream/" in body
