import json
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
TARGET_GLOB = "*_20260507T081859Z/manifest.json"
OUT_JSON = ROOT / "research" / "work" / "terra055_page_anchors_20260507.json"

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "have",
    "has",
    "are",
    "was",
    "were",
    "into",
    "over",
    "under",
    "using",
    "use",
    "based",
    "model",
    "models",
    "paper",
    "study",
    "data",
    "task",
    "tasks",
    "introduction",
    "abstract",
}


def norm_text(text: str) -> str:
    text = text.lower().replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def candidate_tokens(text: str) -> list[str]:
    toks = re.findall(r"[a-zA-Z][a-zA-Z\-]{3,}", text.lower())
    seen = []
    for t in toks:
        if t in STOPWORDS:
            continue
        if t not in seen:
            seen.append(t)
    return seen


@dataclass
class Anchor:
    page: int
    confidence: str
    locator: str
    method: str


def find_anchors(page_texts: list[str], candidates: list[str]) -> list[Anchor]:
    anchors: list[Anchor] = []
    page_norm = [norm_text(t) for t in page_texts]
    for cand in candidates:
        c = norm_text(cand)
        if len(c) < 24:
            continue

        # Strong signal: direct phrase containment
        found_direct = False
        for idx, ptxt in enumerate(page_norm, start=1):
            if c in ptxt:
                anchors.append(
                    Anchor(
                        page=idx,
                        confidence="high",
                        locator=cand[:220],
                        method="direct_phrase",
                    )
                )
                found_direct = True
                break
        if found_direct:
            continue

        # Fallback: token-overlap score
        toks = candidate_tokens(c)
        if len(toks) < 5:
            continue
        key = toks[:10]
        best_page = None
        best_score = 0
        for idx, ptxt in enumerate(page_norm, start=1):
            score = sum(1 for t in key if t in ptxt)
            if score > best_score:
                best_score = score
                best_page = idx
        if best_page is None:
            continue
        if best_score >= 8:
            conf = "medium"
        elif best_score >= 5:
            conf = "low"
        else:
            continue
        anchors.append(
            Anchor(
                page=best_page,
                confidence=conf,
                locator=cand[:220],
                method=f"token_overlap:{best_score}",
            )
        )

    # De-duplicate by page, keep strongest confidence
    rank = {"high": 3, "medium": 2, "low": 1}
    by_page: dict[int, Anchor] = {}
    for a in anchors:
        cur = by_page.get(a.page)
        if cur is None or rank[a.confidence] > rank[cur.confidence]:
            by_page[a.page] = a
    ordered = sorted(by_page.values(), key=lambda x: x.page)[:4]
    return ordered


def main() -> None:
    rows = []
    manifests = sorted((ROOT / "research" / "extracted").glob(TARGET_GLOB))
    for mpath in manifests:
        manifest = json.loads(mpath.read_text(encoding="utf-8"))
        slug = manifest["document_id"]
        source_pdf = ROOT / manifest["source_pdf"]
        excerpt_path = mpath.parent / "ingest_excerpt_abstract_through_intro.txt"
        l4_path = mpath.parent / "l4_analysis.json"
        l2_path = mpath.parent / "l2_outline.json"

        excerpt = excerpt_path.read_text(encoding="utf-8", errors="ignore") if excerpt_path.exists() else ""
        sents = split_sentences(excerpt)

        candidates: list[str] = []
        title = manifest.get("title_hint", "").strip()
        if title:
            candidates.append(title)
        candidates.extend(sents[:2])

        if l4_path.exists():
            try:
                l4 = json.loads(l4_path.read_text(encoding="utf-8"))
                analysis = l4.get("analysis", {})
                if isinstance(analysis, dict):
                    if analysis.get("approach_summary"):
                        candidates.append(str(analysis["approach_summary"]))
                    for kp in analysis.get("key_points", [])[:2]:
                        candidates.append(str(kp))
            except Exception:
                pass

        if l2_path.exists():
            try:
                l2 = json.loads(l2_path.read_text(encoding="utf-8"))
                for o in l2.get("outline", [])[:2]:
                    if isinstance(o, dict) and o.get("summary"):
                        candidates.append(str(o["summary"]))
            except Exception:
                pass

        page_texts = []
        try:
            reader = PdfReader(str(source_pdf))
            for page in reader.pages:
                page_texts.append(page.extract_text() or "")
        except Exception:
            rows.append(
                {
                    "document_id": slug,
                    "source_pdf": manifest["source_pdf"],
                    "anchors": [],
                    "anchor_status": "gap",
                    "gap_reason": "pdf_read_failed",
                }
            )
            continue

        anchors = find_anchors(page_texts, candidates)
        row = {
            "document_id": slug,
            "source_pdf": manifest["source_pdf"],
            "anchors": [
                {
                    "page": a.page,
                    "confidence": a.confidence,
                    "locator": a.locator,
                    "method": a.method,
                }
                for a in anchors
            ],
            "anchor_status": "anchored" if anchors else "gap",
            "gap_reason": None if anchors else "no_reliable_match",
        }
        rows.append(row)

    OUT_JSON.write_text(json.dumps({"documents": rows}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    anchored = sum(1 for r in rows if r["anchor_status"] == "anchored")
    print(f"anchored={anchored} total={len(rows)} out={OUT_JSON}")


if __name__ == "__main__":
    main()
