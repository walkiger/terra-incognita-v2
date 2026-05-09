#!/usr/bin/env python3
"""
JARVIS — ConceptNet API Test
=============================
KEIN API KEY NÖTIG. Kostenlos, offen, mehrsprachig.
Docs: https://conceptnet.io/

FALLS CONCEPTNET GEBLOCKT IST (403):
  → Das Script erkennt das automatisch und zeigt Hinweise.
  → Versuche es lokal oder über VPN.

RUN:
  python3 test_conceptnet.py
  python3 test_conceptnet.py --words mind truth --langs en de fr
  python3 test_conceptnet.py --limit 200  # mehr Kanten pro Wort

WAS DIESER TEST ZEIGT:
  Für jedes Wort × jede Sprache:
  - Synonyme (similar-to)
  - Antonyme (opposite)
  - Hypernyms (is-a)
  - PartOf, Causes, HasProperty, CapableOf
  - Definitionen (DefinedAs)
  - Fremdsprach-Äquivalente (TranslationOf)

FEEDBACK:
  Schick mir test_conceptnet_results.json
  oder den Konsolenoutput.
"""

import sys, os, json, time, argparse
import urllib.request, urllib.parse
from datetime import date

# ── Testwörter ─────────────────────────────────────────────────
TEST_WORDS = [
    "time", "space", "soul", "self", "identity",
    "mind", "knowledge", "consciousness", "belief", "truth",
    "reason", "doubt", "curiosity", "memory", "perception",
    "logic", "existence", "language", "meaning", "reality",
]

LANGUAGES = {
    "en": "English", "de": "Deutsch", "fr": "Français",
    "es": "Español", "it": "Italiano", "ru": "Русский",
}

CN_BASE = "https://api.conceptnet.io"

# ConceptNet rel → preseed rel + weight
REL_MAP = {
    "/r/IsA":                        ("is-a",             0.5),
    "/r/PartOf":                     ("part-of",           0.5),
    "/r/Causes":                     ("causes",            0.5),
    "/r/Entails":                    ("implies",           0.5),
    "/r/HasProperty":                ("has-property",      0.4),
    "/r/RelatedTo":                  ("co-activated-with", 0.35),
    "/r/Synonym":                    ("similar-to",        0.6),
    "/r/Antonym":                    ("opposite",          0.9),
    "/r/DefinedAs":                  ("defined-by",        0.3),
    "/r/DerivedFrom":                ("derived-from",      0.3),
    "/r/CapableOf":                  ("enables",           0.5),
    "/r/UsedFor":                    ("enables",           0.4),
    "/r/MannerOf":                   ("is-a",              0.4),
    "/r/SimilarTo":                  ("similar-to",        0.6),
    "/r/DistinctFrom":               ("opposite",          0.7),
    "/r/EtymologicallyRelatedTo":    ("co-activated-with", 0.3),
    "/r/Desires":                    ("implies",           0.4),
    "/r/CausesDesire":               ("enables",           0.4),
    "/r/HasContext":                  ("co-activated-with", 0.35),
    "/r/FormOf":                     ("inflection-of",     0.8),
    "/r/MadeOf":                     ("part-of",           0.4),
}

# ── Fetch ──────────────────────────────────────────────────────
def get(url, timeout=12):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "JARVIS-preseed-builder/1.0 (research)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return None, str(e)

def fetch_edges(word, lang="en", limit=150):
    node = f"/c/{lang}/{urllib.parse.quote(word.lower().replace(' ','_'))}"
    url  = f"{CN_BASE}/query?node={urllib.parse.quote(node)}&limit={limit}"
    data, err = get(url)
    if err:
        return [], err
    return data.get("edges", []), None

def fetch_translation_edges(word, lang="en", limit=40):
    node = f"/c/{lang}/{urllib.parse.quote(word.lower())}"
    edges = []
    for direction in ["start", "end"]:
        url = (f"{CN_BASE}/query?{direction}={urllib.parse.quote(node)}"
               f"&rel={urllib.parse.quote('/r/TranslationOf')}&limit={limit}")
        data, _ = get(url)
        if data:
            edges.extend(data.get("edges", []))
    return edges

def fetch_definition(word, lang="en"):
    """Try to get DefinedAs edges."""
    node = f"/c/{lang}/{urllib.parse.quote(word.lower())}"
    url  = (f"{CN_BASE}/query?start={urllib.parse.quote(node)}"
            f"&rel={urllib.parse.quote('/r/DefinedAs')}&limit=10")
    data, _ = get(url)
    if not data:
        return []
    return [
        e.get("end", {}).get("label", "")
        for e in data.get("edges", [])
        if e.get("end", {}).get("language", "") == lang
    ]

# ── Parse edges ────────────────────────────────────────────────
def parse_edges(edges, source_word, source_lang="en"):
    """Extract relations from ConceptNet edges."""
    source_node = f"/c/{source_lang}/{source_word.lower()}"

    relations   = []
    synonyms    = []
    antonyms    = []
    defwords    = []
    foreign     = {}
    definitions = []

    for edge in edges:
        rel_id  = edge.get("rel", {}).get("@id", "")
        start   = edge.get("start", {})
        end     = edge.get("end",   {})
        weight  = edge.get("weight", 1.0)
        surface = edge.get("surfaceText", "")

        start_id   = start.get("@id", "")
        end_id     = end.get("@id",   "")
        start_lang = start.get("language", "")
        end_lang   = end.get("language",   "")
        start_lbl  = start.get("label", "").lower().strip()
        end_lbl    = end.get("label",   "").lower().strip()

        if source_node not in (start_id, end_id):
            continue

        # Direction
        if start_id == source_node:
            target, target_lang, direction = end_lbl,   end_lang,   "out"
        else:
            target, target_lang, direction = start_lbl, start_lang, "in"

        if not target or target == source_word.lower():
            continue

        # Translation edges
        if rel_id == "/r/TranslationOf":
            if target_lang in LANGUAGES and target_lang != source_lang:
                if target_lang not in foreign:
                    foreign[target_lang] = []
                if target not in [x["term"] for x in foreign[target_lang]]:
                    foreign[target_lang].append({
                        "term":      target,
                        "weight":    round(weight, 3),
                        "surface":   surface,
                    })
            continue

        # DefinedAs
        if rel_id == "/r/DefinedAs" and target_lang == source_lang:
            definitions.append(target)
            continue

        preseed_rel, preseed_w = REL_MAP.get(rel_id, (None, 0))
        if not preseed_rel:
            continue

        # Only same-language relations for main EN block
        if target_lang != source_lang:
            # Still capture as foreign hint
            if target_lang in LANGUAGES:
                if target_lang not in foreign:
                    foreign[target_lang] = []
                if target not in [x["term"] for x in foreign[target_lang]]:
                    foreign[target_lang].append({
                        "term":    target,
                        "weight":  round(weight, 3),
                        "surface": surface,
                    })
            continue

        # Skip very long phrases
        if len(target) > 35 or (len(target.split()) > 4):
            continue

        if preseed_rel == "similar-to":
            if target not in synonyms: synonyms.append(target)
        elif preseed_rel == "opposite":
            if target not in antonyms: antonyms.append(target)
        elif preseed_rel == "defined-by":
            if target not in defwords: defwords.append(target)

        relations.append({
            "preseed_rel": preseed_rel,
            "target":      target,
            "weight":      preseed_w,
            "cn_rel":      rel_id.replace("/r/",""),
            "cn_weight":   round(weight, 3),
            "surface":     surface[:80] if surface else "",
        })

    # Deduplicate and sort
    seen = set()
    unique = []
    for r in sorted(relations, key=lambda x: -x["cn_weight"]):
        key = (r["preseed_rel"], r["target"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return {
        "synonyms":    synonyms[:15],
        "antonyms":    antonyms[:10],
        "defwords":    defwords[:8],
        "definitions": definitions[:5],
        "relations":   unique[:40],
        "foreign":     {lang: terms[:6] for lang, terms in foreign.items()},
    }

# ── Report ─────────────────────────────────────────────────────
def print_report(word, parsed, edge_count):
    if not parsed:
        return
    print(f"  Edges:      {edge_count}")
    print(f"  Synonyms  ({len(parsed['synonyms'])}):  {parsed['synonyms']}")
    print(f"  Antonyms  ({len(parsed['antonyms'])}):  {parsed['antonyms']}")
    print(f"  DefWords  ({len(parsed['defwords'])}):  {parsed['defwords']}")
    if parsed['definitions']:
        print(f"  DefinedAs ({len(parsed['definitions'])}):")
        for d in parsed['definitions'][:3]:
            print(f"    '{d}'")

    # Relations grouped by type
    by_type = {}
    for r in parsed['relations']:
        by_type.setdefault(r["preseed_rel"], []).append(r["target"])
    print(f"  Relations ({len(parsed['relations'])}):")
    for rel_type in ["is-a","part-of","causes","enables","implies",
                     "has-property","co-activated-with","similar-to","opposite"]:
        targets = by_type.get(rel_type, [])
        if targets:
            print(f"    [{rel_type:20s}]: {targets[:6]}")

    if parsed['foreign']:
        print(f"  Foreign ({len(parsed['foreign'])} langs):")
        for lang, terms in parsed['foreign'].items():
            top = [t['term'] for t in terms[:4]]
            print(f"    [{lang}]: {top}")

# ── Main ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--words",  nargs="+", default=TEST_WORDS)
    parser.add_argument("--langs",  nargs="+", default=["en"])
    parser.add_argument("--limit",  type=int,  default=150)
    parser.add_argument("--output", default="test_conceptnet_results.json")
    args = parser.parse_args()

    print("=" * 60)
    print("  CONCEPTNET — JARVIS PRESEED TEST")
    print(f"  Datum:   {date.today()}")
    print(f"  Wörter:  {len(args.words)}")
    print(f"  Sprachen:{args.langs}")
    print(f"  Limit:   {args.limit} Kanten/Wort")
    print("  Kein API Key nötig")
    print("=" * 60)

    # Connectivity check
    print("\n  Verbindungstest...", end=" ")
    test_data, test_err = get(f"{CN_BASE}/c/en/test?limit=1")
    if test_err:
        print(f"❌ FEHLER: {test_err}")
        print("  ConceptNet ist evtl. geblockt.")
        print("  Versuche es lokal oder über VPN.")
        print("  Docs: https://conceptnet.io/")
        sys.exit(1)
    else:
        print("✅ ConceptNet erreichbar")

    all_results = {}

    for i, word in enumerate(args.words, 1):
        print(f"\n{'─'*60}")
        print(f"  [{i}/{len(args.words)}] {word.upper()}")

        word_result = {}

        for lang in args.langs:
            print(f"  [{lang}] Kanten holen...", end=" ", flush=True)
            edges, err = fetch_edges(word, lang=lang, limit=args.limit)

            if lang == "en":
                # Translations extra
                trans = fetch_translation_edges(word, lang=lang)
                edges += trans
                defs  = fetch_definition(word, lang=lang)
            else:
                defs = []

            print(f"{len(edges)} Kanten")

            if err:
                print(f"    ⚠️  Fehler: {err}")
                word_result[lang] = {"error": err}
                continue

            parsed = parse_edges(edges, word, source_lang=lang)
            if defs:
                parsed["definitions"] = defs + parsed.get("definitions", [])

            if lang == "en":
                print_report(word, parsed, len(edges))

            word_result[lang] = parsed
            time.sleep(0.25)

        all_results[word] = word_result

    # Speichern
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.output)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"  ✅ Gespeichert: {out_path}")
    print(f"\n  FEEDBACK-FRAGEN:")
    print(f"  1. Sind die Synonyme philosophisch korrekt?")
    print(f"  2. Sind die Antonyme richtig?")
    print(f"  3. Wie gut sind is-a, part-of, causes etc.?")
    print(f"  4. Wie viel Rauschen — was muss gefiltert werden?")
    print(f"  5. Sind die DefinedAs-Texte verwendbar als Kurzdef?")
    print(f"  6. Sind Fremdsprachäquivalente korrekte Übersetzungen?")
    print(f"\n  → Schick {args.output} zurück oder kopiere den Output")
    print("=" * 60)

if __name__ == "__main__":
    main()
