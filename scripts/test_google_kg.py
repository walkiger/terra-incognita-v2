#!/usr/bin/env python3
"""
JARVIS — Google Knowledge Graph Search API Test
================================================
SETUP (5 Minuten):
  1. https://console.cloud.google.com/
  2. Neues Projekt oder bestehendes wählen
  3. "APIs & Services" → "Enable APIs"
  4. Suche: "Knowledge Graph Search API" → Enable
  5. "Credentials" → "Create Credentials" → "API Key"
  6. Kostenlos: 100.000 Requests/Tag

RUN:
  export GOOGLE_KG_KEY="dein-key-hier"
  python3 test_google_kg.py

  Oder direkt:
  python3 test_google_kg.py --key dein-key-hier

WAS DIESER TEST ZEIGT:
  Für jedes Wort × jede Sprache (EN/DE/FR/ES/IT/RU):
  - Entity-Name in der jeweiligen Sprache → potential DE/FR/ES/IT/RU key
  - Kurze Beschreibung → potential def (short)
  - Wikipedia-Text → potential def (long)
  - Entity-Types → potential is-a relations
  - GKG Score → Konfidenz

FEEDBACK:
  Schau dir test_google_kg_results.json an.
  Fragen dazu stehen am Ende des Outputs.
  Schick mir die Datei oder kopiere den Output.
"""

import sys, os, json, time, argparse
import urllib.request, urllib.parse
from datetime import date

# ── Testwörter ────────────────────────────────────────────────
# Primordials + Core-20 aus w03/w05 + häufige External Refs
TEST_WORDS = [
    # w00 Primordials
    "time", "space", "soul", "self", "identity",
    # w05 Cognition Core
    "mind", "knowledge", "consciousness", "belief", "truth",
    "reason", "perception", "memory", "imagination", "attention",
    # w03 Existence Core
    "existence", "causality", "emergence", "transformation",
    # External Refs (häufig referenziert, noch nicht im Preseed)
    "cognition", "reality", "meaning", "language", "logic",
]

LANGUAGES  = ["en", "de", "fr", "es", "it", "ru"]
KG_BASE    = "https://kgsearch.googleapis.com/v1/entities:search"

# ── Fetch ─────────────────────────────────────────────────────
def fetch(word, api_key, lang="en", limit=5):
    params = urllib.parse.urlencode({
        "query":     word,
        "key":       api_key,
        "limit":     limit,
        "indent":    True,
        "languages": lang,
    })
    url = f"{KG_BASE}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        return {"error": f"HTTP {e.code}", "detail": body[:200]}
    except Exception as e:
        return {"error": str(e)}

def fetch_word_all_langs(word, api_key):
    results = {}
    for lang in LANGUAGES:
        print(f"    [{lang}]", end=" ", flush=True)
        results[lang] = fetch(word, api_key, lang=lang, limit=5)
        time.sleep(0.12)
    print()
    return results

# ── Parse ─────────────────────────────────────────────────────
def parse(raw, lang="en"):
    if "error" in raw:
        return {"error": raw["error"]}
    items = raw.get("itemListElement", [])
    if not items:
        return {"found": False}

    best   = items[0].get("result", {})
    score  = items[0].get("resultScore", 0)
    name   = best.get("name", "")
    desc   = best.get("description", "")

    detail_obj  = best.get("detailedDescription", {})
    detail_text = ""
    detail_url  = ""
    if isinstance(detail_obj, dict):
        detail_text = detail_obj.get("articleBody", "")
        detail_url  = detail_obj.get("url", "")

    types_raw = best.get("@type", [])
    types = [
        t.replace("http://schema.org/", "").replace("schema:", "")
        for t in types_raw
        if "Thing" not in t and isinstance(t, str)
    ]

    # All items for reference
    all_names = [
        item.get("result", {}).get("name", "")
        for item in items[:5]
        if item.get("result", {}).get("name")
    ]

    return {
        "found":        True,
        "score":        round(score, 2),
        "name":         name if isinstance(name, str) else str(name),
        "description":  desc if isinstance(desc, str) else "",
        "detail":       detail_text[:800] if detail_text else "",
        "wikipedia":    detail_url,
        "types":        types,
        "all_top_names": all_names,
    }

# ── Map to preseed schema ─────────────────────────────────────
def map_to_preseed(word, parsed_by_lang):
    en = parsed_by_lang.get("en", {})
    if not en.get("found"):
        return {"word": word, "found": False}

    # is-a relations from entity types
    isa_rels = []
    for t in en.get("types", []):
        t_low = t.lower().strip()
        if t_low and t_low != word.lower() and len(t_low) > 2:
            isa_rels.append(["is-a", t_low, 0.5])

    # Foreign language data
    foreign = {}
    for lang in ["de", "fr", "es", "it", "ru"]:
        parsed = parsed_by_lang.get(lang, {})
        if not parsed.get("found"):
            continue
        name = parsed.get("name", "").lower().strip()
        if name and name != word.lower() and len(name) > 1:
            foreign[lang] = {
                "suggested_key":  name,
                "description":    parsed.get("description", ""),
                "detail_excerpt": parsed.get("detail", "")[:300],
                "wikipedia":      parsed.get("wikipedia", ""),
                "confidence":     parsed.get("score", 0),
            }

    # Def quality assessment
    short_def = en.get("description", "")
    long_def  = en.get("detail", "")
    def_quality = (
        "excellent" if len(long_def) > 200 else
        "good"      if len(long_def) > 80  else
        "short"     if short_def             else
        "none"
    )

    return {
        "word":                    word,
        "found":                   True,
        "gkg_score":               en.get("score", 0),
        "gkg_types":               en.get("types", []),
        "gkg_description_short":   short_def,
        "gkg_description_long":    long_def,
        "gkg_wikipedia":           en.get("wikipedia", ""),
        "gkg_all_top_names":       en.get("all_top_names", []),
        "def_quality":             def_quality,
        "suggested_isa_relations": isa_rels,
        "foreign_suggestions":     foreign,
        "foreign_coverage":        len(foreign),  # how many langs have data
    }

# ── Report ─────────────────────────────────────────────────────
def print_report(word, mapped):
    SEP = "─" * 60
    print(f"\n{SEP}")
    print(f"  WORD: {word.upper()}")
    if not mapped or not mapped.get("found"):
        print("  ❌  No GKG data")
        return

    print(f"  GKG Score:   {mapped['gkg_score']}")
    print(f"  Types:       {mapped['gkg_types']}")
    print(f"  Def quality: {mapped['def_quality']}")
    print(f"  Short def:   {mapped['gkg_description_short']}")
    if mapped['gkg_description_long']:
        preview = mapped['gkg_description_long'][:300]
        print(f"  Long def:    {preview}...")
    if mapped['gkg_wikipedia']:
        print(f"  Wikipedia:   {mapped['gkg_wikipedia']}")

    if mapped['suggested_isa_relations']:
        print(f"\n  → is-a relations suggested:")
        for r in mapped['suggested_isa_relations']:
            print(f"      {r}")

    if mapped['foreign_suggestions']:
        print(f"\n  → Foreign keys ({len(mapped['foreign_suggestions'])}/{len(LANGUAGES)-1} langs):")
        for lang, data in mapped['foreign_suggestions'].items():
            print(f"      [{lang}] key:'{data['suggested_key']}'  "
                  f"conf:{data['confidence']}  "
                  f"def:'{data['description'][:60]}'")
    else:
        print(f"  ⚠️  No foreign suggestions")

# ── Summary ────────────────────────────────────────────────────
def print_summary(all_results):
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    found      = [w for w, r in all_results.items() if r and r.get("found")]
    not_found  = [w for w, r in all_results.items() if not r or not r.get("found")]
    excellent  = [w for w in found if all_results[w]["def_quality"] == "excellent"]
    good       = [w for w in found if all_results[w]["def_quality"] == "good"]
    full_cover = [w for w in found if all_results[w]["foreign_coverage"] == 5]

    print(f"  Found:           {len(found)}/{len(all_results)}")
    print(f"  Not found:       {not_found}")
    print(f"  Def excellent:   {len(excellent)}  {excellent}")
    print(f"  Def good:        {len(good)}")
    print(f"  Full lang cover: {len(full_cover)}  {full_cover}")

    print(f"\n  FEEDBACK QUESTIONS:")
    print(f"  1. Sind die Entity-Types brauchbar als is-a Relations?")
    print(f"  2. Sind die kurzen Descriptions gut genug als Preseed-Defs?")
    print(f"  3. Sind die Foreign Key Suggestions korrekte Übersetzungen?")
    print(f"  4. Wie gut ist der Wikipedia-Text für längere Defs?")
    print(f"  5. Welche Wörter fehlen komplett — warum?")
    print(f"\n  → Schick test_google_kg_results.json zurück mit Anmerkungen")
    print(f"  → Oder kopiere diesen Output")

# ── Main ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key",    default=os.environ.get("GOOGLE_KG_KEY",""))
    parser.add_argument("--words",  nargs="+", default=TEST_WORDS)
    parser.add_argument("--output", default="test_google_kg_results.json")
    parser.add_argument("--langs",  nargs="+", default=LANGUAGES)
    args = parser.parse_args()

    if not args.key:
        print("=" * 60)
        print("  GOOGLE KG API — KEY FEHLT")
        print("=" * 60)
        print("  Hole deinen Key:")
        print("  1. https://console.cloud.google.com/")
        print("  2. APIs & Services → Enable APIs")
        print("  3. Suche: 'Knowledge Graph Search API' → Enable")
        print("  4. Credentials → Create Credentials → API Key")
        print()
        print("  Dann ausführen:")
        print("  python3 test_google_kg.py --key DEIN_KEY")
        print()
        print("  Oder:")
        print("  export GOOGLE_KG_KEY=DEIN_KEY")
        print("  python3 test_google_kg.py")
        sys.exit(1)

    print("=" * 60)
    print("  GOOGLE KNOWLEDGE GRAPH — JARVIS PRESEED TEST")
    print(f"  Datum: {date.today()}")
    print(f"  Wörter: {len(args.words)}")
    print(f"  Sprachen: {LANGUAGES}")
    print(f"  Requests: ~{len(args.words) * len(LANGUAGES)} API-Calls")
    print("=" * 60)

    all_results = {}

    for i, word in enumerate(args.words, 1):
        print(f"\n[{i}/{len(args.words)}] {word}")
        raw_by_lang    = fetch_word_all_langs(word, args.key)
        parsed_by_lang = {lang: parse(raw_by_lang[lang], lang) for lang in LANGUAGES}
        mapped         = map_to_preseed(word, parsed_by_lang)

        print_report(word, mapped)

        all_results[word] = {
            "mapped": mapped,
            "raw":    raw_by_lang,
        }
        time.sleep(0.2)

    print_summary({w: r["mapped"] for w, r in all_results.items()})

    # Speichern — kompaktes Format ohne raw für Übersicht
    out_dir = os.path.dirname(os.path.abspath(__file__))

    # Full results (mit raw)
    full_path = os.path.join(out_dir, args.output)
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # Kompakt (nur mapped) — leichter zum Durchschauen
    compact_path = os.path.join(out_dir, args.output.replace(".json", "_compact.json"))
    with open(compact_path, 'w', encoding='utf-8') as f:
        json.dump({w: r["mapped"] for w, r in all_results.items()},
                  f, ensure_ascii=False, indent=2)

    print(f"\n  ✅ Gespeichert:")
    print(f"     {full_path}  (vollständig, inkl. raw)")
    print(f"     {compact_path}  (kompakt, nur mapped)")
    print("=" * 60)

if __name__ == "__main__":
    main()
