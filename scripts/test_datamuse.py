#!/usr/bin/env python3
"""
JARVIS — Datamuse API Test
===========================
KEIN API KEY NÖTIG. Kostenlos, schnell, nur Englisch.
Docs: https://www.datamuse.com/api/

WAS DATAMUSE KANN (für uns relevant):
  - Synonyme, Antonyme
  - Hypernyms (übergeordnete Begriffe → is-a)
  - Hyponyms (untergeordnete Begriffe → spezifischere Typen)
  - Trigger-Wörter (stark assoziiert → co-activated-with)
  - "Means like" (bedeutungsähnlich → similar-to)
  - Adjektive für ein Nomen (→ has-property)
  - Nomen für ein Adjektiv (→ has-property)

LIMITATION: Nur Englisch. Keine Relations-Typen außer den oben.
STÄRKE: Schnell, viele Wörter, gute Abdeckung.

RUN:
  python3 test_datamuse.py
  python3 test_datamuse.py --words mind truth doubt
  python3 test_datamuse.py --diff   (vergleicht mit preseed.json)

FEEDBACK:
  Schick test_datamuse_results.json zurück.
"""

import sys, os, json, time, argparse
import urllib.request, urllib.parse
from datetime import date

# ── Testwörter ─────────────────────────────────────────────────
TEST_WORDS = [
    "time", "space", "soul", "self", "identity",
    "mind", "knowledge", "consciousness", "belief", "truth",
    "reason", "doubt", "curiosity", "memory", "perception",
    "logic", "existence", "meaning", "reality", "language",
    "cause", "effect", "change", "structure", "relation",
]

DM_BASE = "https://api.datamuse.com/words"

# Query-Typen mit rel_CODE → preseed mapping
QUERIES = [
    # (name, rel_code, ml_mode, preseed_rel, weight, limit)
    ("synonyms",     "syn",  False, "similar-to",       0.6,  25),
    ("antonyms",     "ant",  False, "opposite",          0.9,  15),
    ("hypernyms",    "gen",  False, "is-a",              0.5,  15),
    ("hyponyms",     "spe",  False, "enables",           0.4,  15),
    ("triggers",     "trg",  False, "co-activated-with", 0.35, 20),
    ("comes_after",  "bga",  False, "co-activated-with", 0.3,  10),
    ("comes_before", "bgb",  False, "co-activated-with", 0.3,  10),
    ("adj_for_noun", "jja",  False, "has-property",      0.4,  15),
    ("noun_for_adj", "jjb",  False, "has-property",      0.4,  15),
    ("means_like",   None,   True,  "similar-to",        0.5,  15),
]

# ── Fetch ──────────────────────────────────────────────────────
def fetch(word, rel_code=None, ml=False, limit=20):
    params = {"max": limit}
    if rel_code:
        params[f"rel_{rel_code}"] = word
    elif ml:
        params["ml"] = word
    else:
        return []
    url = f"{DM_BASE}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "JARVIS-preseed-builder/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"\n    ⚠️  HTTP {e.code}: {e.reason}")
        return []
    except Exception as e:
        print(f"\n    ⚠️  Fehler: {e}")
        return []

def fetch_all(word):
    """Holt alle Datamuse-Abfragetypen für ein Wort."""
    results = {}
    for name, rel_code, ml, preseed_rel, weight, limit in QUERIES:
        raw = fetch(word, rel_code=rel_code, ml=ml, limit=limit)
        results[name] = {
            "terms":        [(item["word"], item.get("score",0)) for item in raw],
            "preseed_rel":  preseed_rel,
            "weight":       weight,
        }
        time.sleep(0.04)
    return results

# ── Map to preseed ─────────────────────────────────────────────
def map_to_preseed(word, raw):
    synonyms  = []
    antonyms  = []
    relations = []
    by_type   = {}
    seen      = set()

    for name, data in raw.items():
        rel    = data["preseed_rel"]
        weight = data["weight"]
        terms  = data["terms"]

        by_type[name] = [t for t,_ in terms]

        for term, score in terms:
            if not term or term == word or len(term) < 2:
                continue
            if len(term) > 35:
                continue

            key = (rel, term)
            if key in seen:
                continue
            seen.add(key)

            if rel == "similar-to" and term not in synonyms:
                synonyms.append(term)
            elif rel == "opposite" and term not in antonyms:
                antonyms.append(term)

            relations.append({
                "preseed_rel": rel,
                "target":      term,
                "weight":      weight,
                "dm_score":    score,
                "source":      name,
            })

    # Sortieren: Antonyme + Synonyme zuerst, dann nach Score
    relations.sort(key=lambda r: (
        0 if r["preseed_rel"] == "opposite" else
        1 if r["preseed_rel"] == "similar-to" else 2,
        -r["dm_score"]
    ))

    return {
        "word":           word,
        "synonyms":       synonyms[:15],
        "antonyms":       antonyms[:10],
        "hypernyms":      by_type.get("hypernyms", [])[:8],
        "hyponyms":       by_type.get("hyponyms",  [])[:8],
        "triggers":       by_type.get("triggers",  [])[:12],
        "means_like":     by_type.get("means_like",[])[:8],
        "adj_for_noun":   by_type.get("adj_for_noun",[])[:8],
        "comes_after":    by_type.get("comes_after",[])[:6],
        "comes_before":   by_type.get("comes_before",[])[:6],
        "all_relations":  relations[:45],
    }

# ── Report ─────────────────────────────────────────────────────
def print_report(mapped):
    if not mapped:
        return
    print(f"  Synonyme   ({len(mapped['synonyms'])}):  {mapped['synonyms']}")
    print(f"  Antonyme   ({len(mapped['antonyms'])}):  {mapped['antonyms']}")
    print(f"  Hypernyms  ({len(mapped['hypernyms'])}): {mapped['hypernyms']}")
    print(f"  Hyponyms   ({len(mapped['hyponyms'])}):{' '*2}{mapped['hyponyms']}")
    print(f"  Triggers   ({len(mapped['triggers'])}):  {mapped['triggers']}")
    print(f"  Means like ({len(mapped['means_like'])}): {mapped['means_like']}")
    if mapped['adj_for_noun']:
        print(f"  Adj→Noun  ({len(mapped['adj_for_noun'])}): {mapped['adj_for_noun']}")
    if mapped['comes_after']:
        print(f"  Comes after:  {mapped['comes_after']}")
    print(f"  Total relations: {len(mapped['all_relations'])}")

# ── Diff vs preseed ────────────────────────────────────────────
def diff_vs_preseed(word, mapped, preseed_path):
    try:
        with open(preseed_path, encoding='utf-8') as f:
            p = json.load(f)
    except:
        return None

    existing = None
    for wave_key in [k for k in p if not k.startswith('_')]:
        en = p[wave_key].get('en', {})
        if word in en:
            existing = en[word]
            break
    if not existing:
        return {"status": "not_in_preseed"}

    ex_syns = set(existing.get('synonyms', []))
    ex_ants = set(existing.get('antonyms', []))
    ex_rels = {(r[0], r[1]) for r in existing.get('relations', []) if len(r) >= 2}

    dm_syns = set(mapped['synonyms'])
    dm_ants = set(mapped['antonyms'])
    dm_rels = {(r["preseed_rel"], r["target"]) for r in mapped['all_relations']}

    return {
        "new_synonyms":       sorted(dm_syns - ex_syns),
        "new_antonyms":       sorted(dm_ants - ex_ants),
        "new_relations":      sorted(dm_rels - ex_rels),
        "confirmed_synonyms": sorted(dm_syns & ex_syns),
        "confirmed_antonyms": sorted(dm_ants & ex_ants),
        "preseed_only_syns":  sorted(ex_syns - dm_syns),
        "preseed_only_ants":  sorted(ex_ants - dm_ants),
    }

# ── Main ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--words",  nargs="+", default=TEST_WORDS)
    parser.add_argument("--output", default="test_datamuse_results.json")
    parser.add_argument("--diff",   action="store_true",
                        help="Vergleich mit existierender preseed.json")
    args = parser.parse_args()

    preseed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "preseed.json")

    print("=" * 60)
    print("  DATAMUSE — JARVIS PRESEED TEST")
    print(f"  Datum:  {date.today()}")
    print(f"  Wörter: {len(args.words)}")
    print(f"  Nur Englisch. Kein API Key nötig.")
    print("=" * 60)

    # Verbindungstest
    print("\n  Verbindungstest...", end=" ")
    test = fetch("time", rel_code="syn", limit=2)
    if test:
        print(f"✅ Datamuse erreichbar (test: syn(time)={[t['word'] for t in test]})")
    else:
        print("❌ Kein Response. Evtl. geblockt.")
        print("  Versuche es lokal: https://www.datamuse.com/api/")
        sys.exit(1)

    all_results = {}

    for i, word in enumerate(args.words, 1):
        print(f"\n{'─'*60}")
        print(f"  [{i}/{len(args.words)}] {word.upper()}")
        raw    = fetch_all(word)
        mapped = map_to_preseed(word, raw)
        print_report(mapped)

        if args.diff and os.path.exists(preseed_path):
            diff = diff_vs_preseed(word, mapped, preseed_path)
            if diff and diff.get("status") != "not_in_preseed":
                print(f"\n  ⚡ DIFF vs. preseed:")
                if diff["new_synonyms"]:
                    print(f"    Neue Synonyme:  {diff['new_synonyms']}")
                if diff["new_antonyms"]:
                    print(f"    Neue Antonyme:  {diff['new_antonyms']}")
                if diff["new_relations"]:
                    print(f"    Neue Relations: {list(diff['new_relations'])[:8]}")
                if diff["confirmed_synonyms"]:
                    print(f"    ✅ Bestätigt:    {diff['confirmed_synonyms']}")
                if diff["preseed_only_syns"]:
                    print(f"    ❓ Nur Preseed:  {diff['preseed_only_syns']}")
            elif diff and diff.get("status") == "not_in_preseed":
                print(f"    ℹ️  '{word}' noch nicht im Preseed")

        all_results[word] = {"raw": raw, "mapped": mapped}

    # Speichern
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.output)
    # Kompakt: nur mapped
    compact = {w: r["mapped"] for w, r in all_results.items()}
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(compact, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"  ✅ Gespeichert: {out_path}")
    print(f"\n  FEEDBACK-FRAGEN:")
    print(f"  1. Sind die Synonyme philosophisch brauchbar?")
    print(f"  2. Sind die Antonyme korrekt?")
    print(f"  3. Sind Hypernyms (is-a) verlässlich?")
    print(f"  4. Wie gut sind Trigger für co-activated-with?")
    print(f"  5. Wieviel Rauschen — was braucht Filter?")
    print(f"  6. Lohnt --diff für alle Wörter?")
    print(f"\n  → Schick {args.output} zurück oder kopiere den Output")
    print("=" * 60)

if __name__ == "__main__":
    main()
