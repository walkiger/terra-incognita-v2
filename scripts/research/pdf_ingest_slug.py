#!/usr/bin/env python3
"""Extract IEEE-style header (title before Abstract) and slice Abstract→Intro end.

Outputs suggested basename slug + copies PDF into research/incoming/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import shutil
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _slug(s: str, max_len: int = 72) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:max_len].strip("_") or "document"


def _take_early_pages(reader: PdfReader, max_pages: int = 12, max_chars: int = 28000) -> str:
    chunks: list[str] = []
    n = 0
    for i, page in enumerate(reader.pages):
        if i >= max_pages:
            break
        chunks.append(page.extract_text() or "")
        n += len(chunks[-1])
        if n >= max_chars:
            break
    return "\n".join(chunks)


def _strip_trailing_author_fragment(line: str) -> str:
    """Remove ' … Author1, Author2' tail often glued on same line as title."""
    m = re.search(
        r"\s+(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4})\d(?:\s*[,:]|\s*$)",
        line,
    )
    if m:
        line = line[: m.start()].strip()
    return line


def _looks_like_author_name_csv(ln: str) -> bool:
    """Heuristic: several comma-separated short capitalized name chunks."""
    if ln.count(",") < 2:
        return False
    if ":" in ln:
        return False
    chunks = [c.strip() for c in ln.split(",")]
    if len(chunks) < 3:
        return False
    return all(len(c.split()) <= 4 for c in chunks[:8])


def _looks_author_affiliation_line(ln: str) -> bool:
    if not ln:
        return False
    if "@" in ln or "}@" in ln:
        return True
    # Gabriel Antonesi a , Tudor …
    if re.search(r"\s+[a-z]\s*,", ln):
        return True
    if _looks_like_author_name_csv(ln):
        return True
    if re.search(r"\bdept\.|department\b|university\b|college\b|institute\b", ln, re.I):
        return True
    # Zhou a, 1, Ganqu …
    if re.search(r"\b[a-z]\s*,\s*\d+\s*,", ln):
        return True
    # Wu3,* style
    if re.search(r"\b[A-Za-z][a-z]+\d+\s*,\s*\*", ln):
        return True
    # Multiple superscript-name commas: Zeng1, … Wang1,
    if len(re.findall(r"\b[A-Za-z][a-z]+\d+\s*,", ln)) >= 2:
        return True
    # Single line author enumeration with digit suffixes
    if re.search(r"^[A-Za-z][a-z]+\d+\s*,", ln.strip()):
        return True
    return False


def _strip_probable_given_name_tail(title: str) -> str:
    """PDF text often glues the first author's given name after the title line."""
    return re.sub(
        r"\s+[A-Z][a-z]{2,14}$",
        "",
        title,
        count=1,
        flags=re.UNICODE,
    )


def _extract_title(header: str) -> str:
    lines = [ln.strip() for ln in header.replace("\r", "").split("\n")]
    title_parts: list[str] = []
    for ln in lines:
        if not ln:
            if title_parts:
                break
            continue
        ln = _strip_trailing_author_fragment(ln)
        if not ln:
            continue
        joined = " ".join(title_parts)
        if joined and len(joined) > 35 and re.match(r"^[A-Z][a-z]+\s+[A-Z][a-z]+$", ln):
            break
        if _looks_author_affiliation_line(ln):
            break
        if _looks_author_affiliation_line(_strip_trailing_author_fragment(ln)):
            break
        title_parts.append(ln)
    title = " ".join(title_parts).strip()
    # Second pass: remove stray trailing given name (no digit in extracted text)
    if re.search(
        r"(?:Learning|forecasting|problems|Survey|applications)\s+[A-Z][a-z]{2,14}$",
        title,
    ):
        title = _strip_probable_given_name_tail(title)
    return title or "untitled"


def _slice_abstract_through_intro(early: str) -> tuple[str, str]:
    """Return (title_guess, excerpt from abstract/index through end intro)."""
    low = early.lower()
    abs_m = re.search(r"\babstract\b", early, re.I)
    if not abs_m:
        header = early[:1200]
        excerpt = early[:4000]
        return _extract_title(header), excerpt

    header = early[: abs_m.start()]
    title = _extract_title(header)

    tail = early[abs_m.start() :]

    intro_mark = re.search(
        r"(?:^|\n)\s*(?:I\.|1\.)\s*INTRODUCTION\b",
        tail,
        re.I | re.M,
    )
    start_intro = intro_mark.end() if intro_mark else 0
    after_intro = tail[start_intro:]

    end_m = re.search(
        r"(?:^|\n)\s*(?:II\.|III\.|IV\.|V\.|2\.|3\.)\s+[A-Z][^\n]{0,120}",
        after_intro,
        re.I | re.M,
    )
    if end_m:
        intro_body = after_intro[: end_m.start()]
        excerpt = tail[: start_intro + end_m.start()]
    else:
        excerpt = tail[:12000]

    return title, excerpt


def ingest_one(src: Path, incoming: Path, extracted_root: Path, ts: str, dry_run: bool) -> dict:
    reader = PdfReader(str(src))
    early = _take_early_pages(reader)
    title, excerpt = _slice_abstract_through_intro(early)
    slug = _slug(title)
    basename = f"{slug}_{ts}.pdf"
    doc_id = Path(basename).stem

    dest_pdf = incoming / basename
    dest_dir = extracted_root / doc_id
    manifest = {
        "manifest_version": "0.1.0",
        "document_id": doc_id,
        "source_pdf": f"research/incoming/{basename}",
        "title_hint": title[:500],
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "layers": {
            "L0": {
                "status": "complete",
                "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "artifacts": [f"research/incoming/{basename}"],
                "reason": "",
            },
            "L1": {"status": "pending"},
            "L2": {"status": "pending"},
            "L3": {"status": "pending"},
            "L4": {"status": "pending"},
        },
        "notes": (
            f"Ingest slug from title + excerpt (abstract through end of introduction). excerpt_chars={len(excerpt)}"
        ),
    }
    # R1: canonical file hash (schema-optional top-level); dry_run uses source bytes == eventual dest.
    manifest["pdf_sha256"] = _sha256_file(src)

    out = {
        "src": str(src),
        "title": title,
        "basename": basename,
        "document_id": doc_id,
        "dest_pdf": str(dest_pdf),
        "manifest": manifest,
        "excerpt_preview": excerpt[:600].replace("\n", " ") + ("…" if len(excerpt) > 600 else ""),
    }

    if dry_run:
        return out

    incoming.mkdir(parents=True, exist_ok=True)
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest_pdf)
    manifest["pdf_sha256"] = _sha256_file(dest_pdf)
    excerpt_path = dest_dir / "ingest_excerpt_abstract_through_intro.txt"
    excerpt_path.write_text(excerpt, encoding="utf-8")
    manifest["layers"]["L0"]["artifacts"].append(
        f"research/extracted/{doc_id}/ingest_excerpt_abstract_through_intro.txt"
    )

    (dest_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="+", type=Path, help="Source PDF paths")
    ap.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repo root (contains research/)",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--ts-lowercase",
        action="store_true",
        help=(
            "Lowercase the UTC batch suffix characters (t/z instead of T/Z). "
            "Matches widened manifest schema; default remains strftime uppercase."
        ),
    )
    args = ap.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if args.ts_lowercase:
        ts = ts.lower()
    incoming = args.repo_root / "research" / "incoming"
    extracted_root = args.repo_root / "research" / "extracted"

    rows = []
    for src in args.pdfs:
        src = src.expanduser().resolve()
        if not src.exists():
            raise SystemExit(f"missing: {src}")
        rows.append(ingest_one(src, incoming, extracted_root, ts, args.dry_run))

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass
    for r in rows:
        print(json.dumps(r, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
