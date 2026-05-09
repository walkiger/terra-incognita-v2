#!/usr/bin/env python3
"""
Preseed Knowledge Base Verifier.

Läuft am Anfang jeder Session:
    python3 knowledge/verify.py
    python3 knowledge/verify.py --preseed /pfad/zur/preseed.json
    python3 knowledge/verify.py --wave w03_existence
    python3 knowledge/verify.py --quiet   # nur Zahlen, keine Details

Ausgabe:
    - Quality Check: fehlende similar-to/opposite/defined-by
    - Relation-Typ-Validierung: ungültige Typen/Gewichte
    - Def-Qualität: Leerstrings, zu kurze Defs für Core-Einträge
    - N-Parity: alle Sprachen gleich viele Einträge
    - Externe Referenzen: referenzierte Wörter die fehlen
    - Stats: Fortschritt pro Wave + Sprache
    - Aktualisiert _status und _meta.stats in preseed.json
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Optional

# ── Gültige Relation-Typen (aus ARCHITECTURE.md) ─────────────
VALID_REL_TYPES = {
    'is-a', 'part-of', 'causes', 'prevents', 'enables',
    'depends-on', 'implies', 'defined-by', 'has-property',
    'similar-to', 'opposite', 'contradicts', 'co-activated-with',
    'cross-language', 'cross-language-peer',
    'inflection-of', 'derived-from',
    'example-of', 'answered-by',
}

WEIGHT_MIN = 0.0
WEIGHT_MAX = 1.0

LANGS = ['en', 'de', 'fr', 'es', 'it', 'ru']

# Mindest-Satzanzahl für Core-Entries (nicht Inflektionen)
CORE_MIN_SENTENCES = 2

# Wave-Erwartungen (aus _meta.word_lists oder Fallback)
WAVE_EXPECTED = {
    'w00_primordials':              5,
    'w01_questions_and_structure': 85,
    'w02_grammar_and_structure':   63,
    'w03_existence':              192,
    'w04_space':                  175,
    'w05_cognition':              191,
    'w06_language':               153,
    'w07_action':                 153,
    'w08_values':                 164,
    'w09_social':                 133,
    'w10_number':                 131,
    'w11_physics':                159,
    'w12_discourse':              783,
}


def load(path: str) -> dict:
    """Lädt preseed.json. Bricht mit klarer Fehlermeldung ab."""
    p = Path(path)
    if not p.exists():
        sys.exit(f"FEHLER: {path} nicht gefunden.\n"
                 f"Pfad konfigurierbar: --preseed /pfad/zur/preseed.json")
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def save(p: dict, path: str) -> None:
    """Schreibt preseed.json zurück."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(p, f, ensure_ascii=False, indent=2)


def waves(p: dict) -> list[str]:
    """Gibt alle Wave-Keys zurück (ohne _-prefixed Meta-Keys)."""
    return [k for k in p if not k.startswith('_')]


# ── 1. QUALITY CHECK ─────────────────────────────────────────
def quality_check(p: dict, only_wave: Optional[str] = None) -> dict:
    """
    Prüft Quality-Rules für alle EN-Einträge:
    - Jedes Synonym muss als similar-to in relations stehen
    - Jedes Antonym muss als opposite in relations stehen
    - Jedes defWord muss als defined-by in relations stehen
    - Def darf nicht leer sein
    - Core-Entries (nicht Inflektionen): mind. 2 Sätze

    Returns:
        dict[wave_key -> list[str]]: Issues pro Wave.
    """
    issues = defaultdict(list)

    target_waves = [only_wave] if only_wave else waves(p)

    for wave in target_waves:
        if wave not in p:
            continue
        en = p[wave].get('en', {})
        for word, entry in en.items():
            if not isinstance(entry, dict):
                continue
            if entry.get('_placeholder'):
                continue

            # Def leer oder fehlend
            defn = entry.get('def', '')
            if not defn or not defn.strip():
                issues[wave].append(f"EMPTY_DEF: {word}")
                continue

            rel_pairs = [
                (r[0], r[1])
                for r in entry.get('relations', [])
                if isinstance(r, list) and len(r) >= 2
            ]
            rel_types_seen = {r[0] for r in rel_pairs}

            # Synonyms → similar-to
            for syn in entry.get('synonyms', []):
                if not any(t == 'similar-to' and tgt == syn
                           for t, tgt in rel_pairs):
                    issues[wave].append(
                        f"MISSING similar-to '{syn}' in {word}.relations"
                    )

            # Antonyms → opposite
            for ant in entry.get('antonyms', []):
                if not any(t == 'opposite' and tgt == ant
                           for t, tgt in rel_pairs):
                    issues[wave].append(
                        f"MISSING opposite '{ant}' in {word}.relations"
                    )

            # defWords → defined-by
            for dw in entry.get('defWords', []):
                if not any(t == 'defined-by' and tgt == dw
                           for t, tgt in rel_pairs):
                    issues[wave].append(
                        f"MISSING defined-by '{dw}' in {word}.relations"
                    )

            # Def-Länge: Core-Entries (keine Inflektionen)
            is_inflection = bool(entry.get('inflection_of'))
            if not is_inflection:
                sentences = [
                    s for s in re.split(r'[.!?]+', defn) if s.strip()
                ]
                if len(sentences) < CORE_MIN_SENTENCES:
                    issues[wave].append(
                        f"SHORT_DEF ({len(sentences)} sentence): {word}"
                    )

    return dict(issues)


# ── 2. RELATIONS SCHEMA VALIDATION ───────────────────────────
def relations_check(p: dict, only_wave: Optional[str] = None) -> dict:
    """
    Prüft Relation-Typen und -Gewichte gegen Schema.
    - Typ muss in VALID_REL_TYPES stehen
    - Gewicht muss float in [0.0, 1.0] sein

    Returns:
        dict[wave_key -> list[str]]: Schema-Verletzungen pro Wave.
    """
    issues = defaultdict(list)

    target_waves = [only_wave] if only_wave else waves(p)

    for wave in target_waves:
        if wave not in p:
            continue
        en = p[wave].get('en', {})
        for word, entry in en.items():
            if not isinstance(entry, dict) or entry.get('_placeholder'):
                continue
            for i, rel in enumerate(entry.get('relations', [])):
                if not isinstance(rel, list) or len(rel) < 2:
                    issues[wave].append(
                        f"MALFORMED_REL [{i}] in {word}: {rel}"
                    )
                    continue

                rel_type = rel[0]
                if rel_type not in VALID_REL_TYPES:
                    issues[wave].append(
                        f"INVALID_REL_TYPE '{rel_type}' in {word}"
                    )

                if len(rel) >= 3:
                    weight = rel[2]
                    if not isinstance(weight, (int, float)):
                        issues[wave].append(
                            f"NON_NUMERIC_WEIGHT in {word}.{rel_type}: {weight}"
                        )
                    elif not (WEIGHT_MIN <= float(weight) <= WEIGHT_MAX):
                        issues[wave].append(
                            f"WEIGHT_OOB {weight} in {word}.{rel_type} "
                            f"(expected {WEIGHT_MIN}–{WEIGHT_MAX})"
                        )

    return dict(issues)


# ── 3. N-PARITY CHECK ────────────────────────────────────────
def parity_check(p: dict) -> list[str]:
    """
    Prüft dass alle Sprachen gleich viele Einträge haben wie EN.
    Gibt Liste von Abweichungen zurück.
    """
    issues = []
    for wave in waves(p):
        en_n = len(p[wave].get('en', {}))
        for lang in LANGS:
            n = len(p[wave].get(lang, {}))
            if n != en_n:
                issues.append(
                    f"{wave}: en={en_n} aber {lang}={n} "
                    f"(delta: {en_n - n})"
                )
    return issues


# ── 4. WAVE COMPLETENESS ─────────────────────────────────────
def completeness_check(p: dict) -> list[str]:
    """
    Prüft ob Wave-Wortanzahl mit Erwartung übereinstimmt.
    Hilft verlorene Einträge zu erkennen.
    """
    issues = []
    for wave, expected in WAVE_EXPECTED.items():
        if wave not in p:
            issues.append(f"{wave}: fehlt komplett!")
            continue
        actual = len(p[wave].get('en', {}))
        if actual != expected:
            issues.append(
                f"{wave}: {actual}/{expected} EN-Einträge "
                f"({'zu wenig' if actual < expected else 'zu viele'})"
            )
    return issues


# ── 5. EXTERNAL REFERENCE SCAN ───────────────────────────────
def ext_ref_scan(p: dict) -> tuple[Counter, dict]:
    """
    Findet Wörter die referenziert werden (synonyms, antonyms,
    defWords, relation targets) aber nicht als EN-Eintrag existieren.

    Returns:
        (Counter[word -> count], dict[word -> set_of_sources])
    """
    all_keys: set[str] = set()
    for wave in waves(p):
        all_keys.update(p[wave].get('en', {}).keys())

    ref_counter: Counter = Counter()
    ref_sources: dict = defaultdict(set)

    for wave in waves(p):
        en = p[wave].get('en', {})
        for word, entry in en.items():
            if not isinstance(entry, dict) or entry.get('_placeholder'):
                continue
            candidates: set[str] = set()
            candidates.update(entry.get('synonyms', []))
            candidates.update(entry.get('antonyms', []))
            candidates.update(entry.get('defWords', []))
            for rel in entry.get('relations', []):
                if isinstance(rel, list) and len(rel) >= 2:
                    candidates.add(rel[1])

            for cand in candidates:
                if (isinstance(cand, str)
                        and len(cand) > 2
                        and cand not in all_keys
                        and not cand.startswith('_')):
                    ref_counter[cand] += 1
                    ref_sources[cand].add(word)

    # External refs in _meta aktualisieren
    if '_meta' in p:
        ext = p['_meta'].setdefault('external_refs', {})
        for word, count in ref_counter.most_common():
            priority = ('high' if count > 3
                        else 'medium' if count > 1 else 'low')
            entry = ext.setdefault(word, {
                'referenced_by': [],
                'count': 0,
                'in_preseed': False,
                'priority': priority,
            })
            entry['count'] = count
            entry['priority'] = priority
            entry['in_preseed'] = word in all_keys
            entry['referenced_by'] = list(ref_sources[word])[:10]

        # Aufgelöste Refs aktualisieren
        for word in list(ext.keys()):
            if isinstance(ext[word], dict):
                ext[word]['in_preseed'] = word in all_keys

    return ref_counter, dict(ref_sources)


# ── 6. STATS ─────────────────────────────────────────────────
def update_stats(p: dict, quality_issues: dict) -> tuple[dict, dict]:
    """
    Berechnet Fortschritts-Statistiken pro Wave + Sprache.
    Setzt quality_approved nur wenn 0 Quality-Issues.

    Returns:
        (totals, wave_stats)
    """
    wave_stats = {}
    totals = {
        lang: {'n': 0, 'def': 0, 'skeleton': 0, 'placeholder': 0}
        for lang in LANGS
    }
    complete_en_de = 0
    quality_approved_waves = []

    for wave in waves(p):
        ws = {}
        for lang in LANGS:
            entries = p[wave].get(lang, {})
            rd  = sum(1 for v in entries.values()
                      if isinstance(v, dict)
                      and v.get('def')
                      and v.get('def', '').strip()
                      and not v.get('_placeholder'))
            sk  = sum(1 for v in entries.values()
                      if isinstance(v, dict)
                      and not v.get('def', '').strip()
                      and not v.get('_placeholder'))
            ph  = sum(1 for v in entries.values()
                      if isinstance(v, dict) and v.get('_placeholder'))
            tot = len(entries)
            expected = WAVE_EXPECTED.get(wave, tot)

            if rd == tot > 0:
                status = 'complete'
            elif rd > 0 and ph == 0:
                status = 'partial'
            elif sk > 0 and ph == 0 and rd == 0:
                status = 'skeleton'
            elif ph > 0 and rd == 0:
                status = 'placeholder'
            elif tot == 0:
                status = 'empty'
            else:
                status = 'mixed'

            ws[lang] = {
                'n': tot, 'def': rd, 'skeleton': sk,
                'placeholder': ph, 'status': status,
                'expected': expected if lang == 'en' else None,
            }
            totals[lang]['n']           += tot
            totals[lang]['def']         += rd
            totals[lang]['skeleton']    += sk
            totals[lang]['placeholder'] += ph

        wave_stats[wave] = {'languages': ws}

        # EN+DE complete
        if (ws['en']['status'] == 'complete'
                and ws['de']['status'] == 'complete'):
            complete_en_de += 1

        # Quality-approved: EN complete UND 0 Quality-Issues
        wave_q_issues = len(quality_issues.get(wave, []))
        if ws['en']['status'] == 'complete' and wave_q_issues == 0:
            quality_approved_waves.append(wave)

    for lang in LANGS:
        t = totals[lang]
        pct = round(t['def'] * 100 / t['n'], 1) if t['n'] else 0.0
        totals[lang]['def_pct'] = f"{pct}%"

    totals['_waves_complete_en_de'] = complete_en_de
    totals['_quality_approved'] = quality_approved_waves

    if '_meta' in p:
        p['_meta'].setdefault('stats', {})
        p['_meta']['stats']['waves']  = wave_stats
        p['_meta']['stats']['totals'] = totals
        p['_meta']['stats']['_updated'] = str(date.today())

    return totals, wave_stats


# ── 7. STATUS UPDATE ─────────────────────────────────────────
def update_status(
    p: dict,
    totals: dict,
    q_count: int,
    schema_count: int,
    parity_issues: list,
    quality_approved: list,
) -> None:
    """Aktualisiert _status in preseed.json."""
    if '_status' not in p:
        return
    s = p['_status']
    s['last_verify']              = str(date.today())
    s['quality_issues_count']     = q_count
    s['schema_issues_count']      = schema_count
    s['parity_issues_count']      = len(parity_issues)
    s['waves_en_quality_approved'] = quality_approved


def default_preseed_path() -> str:
    """Default JSON next to this script: prefer preseed_v2.json, else preseed.json."""
    base = Path(__file__).resolve().parent
    for name in ("preseed_v2.json", "preseed.json"):
        candidate = base / name
        if candidate.is_file():
            return str(candidate)
    return str(base / "preseed.json")


# ── MAIN ─────────────────────────────────────────────────────
def main() -> None:
    """Hauptroutine. Argumente: --preseed, --wave, --quiet."""
    parser = argparse.ArgumentParser(
        description="Preseed Knowledge Base Verifier"
    )
    parser.add_argument(
        '--preseed',
        default=default_preseed_path(),
        help=(
            "Pfad zur Preseed-JSON "
            "(Default: preseed_v2.json falls vorhanden, sonst preseed.json)"
        ),
    )
    parser.add_argument(
        '--wave',
        default=None,
        help="Nur diese Wave prüfen (z.B. w03_existence)",
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help="Nur Zusammenfassung, keine Issue-Details",
    )
    args = parser.parse_args()

    SEP  = "─" * 60
    SEP2 = "═" * 60

    print(SEP2)
    print("  PRESEED VERIFIER")
    print(f"  {date.today()}  ·  {args.preseed}")
    if args.wave:
        print(f"  Fokus: {args.wave}")
    print(SEP2)

    p = load(args.preseed)

    # _status anzeigen
    if '_status' in p:
        s = p['_status']
        print(f"\n📍 FOCUS: {s.get('current_focus', '?')}")
        print(f"   NEXT:  {s.get('next_action', '?')}")

    # ── 1. Quality ───────────────────────────────────────────
    print(f"\n{SEP}")
    print("  QUALITY CHECK (synonym→similar-to, antonym→opposite, defWord→defined-by)")
    print(SEP)
    q_issues = quality_check(p, only_wave=args.wave)
    q_total  = sum(len(v) for v in q_issues.values())

    if q_total == 0:
        print("  ✅ Keine Quality-Issues")
    else:
        print(f"  ⚠️  {q_total} Issues:")
        for wave, issues in q_issues.items():
            n = len(issues)
            print(f"\n  [{wave}] — {n} Issues")
            if not args.quiet:
                show = issues[:15]
                for iss in show:
                    print(f"    {iss}")
                if n > 15:
                    print(f"    ... und {n-15} weitere")
                    print(f"    (für alle: --wave {wave})")

    # ── 2. Schema ────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  RELATIONS SCHEMA (Typ-Validierung + Gewichte)")
    print(SEP)
    s_issues = relations_check(p, only_wave=args.wave)
    s_total  = sum(len(v) for v in s_issues.values())

    if s_total == 0:
        print("  ✅ Alle Relation-Typen und Gewichte gültig")
    else:
        print(f"  ⚠️  {s_total} Schema-Verletzungen:")
        for wave, issues in s_issues.items():
            print(f"\n  [{wave}]")
            for iss in (issues if args.quiet else issues[:10]):
                print(f"    {iss}")

    # ── 3. Parity ────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  N-PARITY (alle Sprachen = n(EN))")
    print(SEP)
    p_issues = parity_check(p)
    if not p_issues:
        print("  ✅ Alle Waves: n(EN) == n(alle Sprachen)")
    else:
        for iss in p_issues:
            print(f"  ⚠️  {iss}")

    # ── 4. Completeness ──────────────────────────────────────
    print(f"\n{SEP}")
    print("  WAVE COMPLETENESS (Wortanzahl vs. Erwartung)")
    print(SEP)
    c_issues = completeness_check(p)
    if not c_issues:
        print("  ✅ Alle Wave-Größen stimmen")
    else:
        for iss in c_issues:
            print(f"  ⚠️  {iss}")

    # ── 5. External Refs ─────────────────────────────────────
    print(f"\n{SEP}")
    print("  EXTERNE REFERENZEN (referenziert aber fehlend)")
    print(SEP)
    ref_counter, _ = ext_ref_scan(p)
    high   = [(w, c) for w, c in ref_counter.most_common() if c > 3]
    medium = [(w, c) for w, c in ref_counter.most_common() if c in (2, 3)]
    print(f"  Gesamt: {len(ref_counter)} externe Refs")
    print(f"  High (>3 Referenzen): {len(high)}")
    if high and not args.quiet:
        print(f"    {[w for w, _ in high[:15]]}")
    print(f"  Medium (2-3): {len(medium)}")

    # ── 6. Stats ─────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  FORTSCHRITT")
    print(SEP)
    totals, wave_stats = update_stats(p, q_issues)
    quality_approved   = totals.get('_quality_approved', [])

    for lang in LANGS:
        t = totals[lang]
        filled = '█' * (t['def'] * 20 // max(t['n'], 1))
        empty  = '░' * (20 - len(filled))
        print(f"  {lang}: {t['n']:5d} | "
              f"{t['def']:5d} def ({t['def_pct']:>6}) "
              f"|{filled}{empty}|")

    en_complete = sum(
        1 for ws in wave_stats.values()
        if ws['languages']['en']['status'] == 'complete'
    )
    print(f"\n  Waves EN komplett:          {en_complete}/13")
    print(f"  Waves EN+DE komplett:       {totals['_waves_complete_en_de']}/13")
    print(f"  Waves quality-approved:     {len(quality_approved)}/13")
    if quality_approved:
        print(f"    ✅ {quality_approved}")

    # ── Wave-Tabelle ─────────────────────────────────────────
    if not args.quiet:
        print(f"\n{SEP}")
        print("  WAVE-DETAIL")
        print(SEP)
        print(f"  {'Wave':<30} {'EN':>5} {'DE':>5} "
              f"{'Q-OK':>5} {'Status EN'}")
        print(f"  {'─'*30} {'─'*5} {'─'*5} {'─'*5} {'─'*12}")
        for wave in waves(p):
            ws  = wave_stats.get(wave, {}).get('languages', {})
            en  = ws.get('en', {})
            de  = ws.get('de', {})
            qok = "✅" if wave in quality_approved else f"{len(q_issues.get(wave,[]))}⚠"
            exp = en.get('expected') or WAVE_EXPECTED.get(wave, '?')
            en_def = en.get('def', 0)
            de_def = de.get('def', 0)
            st  = en.get('status', '?')
            print(f"  {wave:<30} {en_def:>3}/{exp:<3} "
                  f"{de_def:>5} {qok:>5} {st}")

    # ── Speichern ────────────────────────────────────────────
    update_status(
        p, totals, q_total, s_total, p_issues, quality_approved
    )
    save(p, args.preseed)

    print(f"\n{SEP2}")
    print("  GESPEICHERT — _status + _meta.stats + external_refs")
    print(SEP2)

    # Exit code: 0 = alles ok, 1 = issues vorhanden
    has_issues = q_total > 0 or s_total > 0 or len(p_issues) > 0
    sys.exit(1 if has_issues else 0)


if __name__ == '__main__':
    main()
