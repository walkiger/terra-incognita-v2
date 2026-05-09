═══════════════════════════════════════════════════════════════
  JARVIS PRESEED — API TEST SCRIPTS
  Datum: 2026-05-03
═══════════════════════════════════════════════════════════════

Drei Scripts zum lokalen Ausführen. Ergebnisse zurück an Claude.

───────────────────────────────────────────────────────────────
  1. GOOGLE KNOWLEDGE GRAPH  →  test_google_kg.py
───────────────────────────────────────────────────────────────
  WARUM: Multilinguale Entity-Defs + Wikipedia + is-a types
  KEY:   Nötig. Kostenlos. 100.000 Requests/Tag.

  Setup:
    1. https://console.cloud.google.com/
    2. APIs & Services → Enable APIs
    3. Suche "Knowledge Graph Search API" → Enable
    4. Credentials → Create Credentials → API Key

  Run:
    python3 test_google_kg.py --key DEIN_KEY

  Output:
    test_google_kg_results.json        (vollständig, mit raw)
    test_google_kg_results_compact.json (nur mapped data)

  Zeigt pro Wort:
    - Entity-Typen → is-a Relations
    - Kurze Beschreibung (EN) → short def
    - Wikipedia-Text (EN) → long def
    - Name in DE/FR/ES/IT/RU → foreign key suggestions
    - Beschreibung in DE/FR/ES/IT/RU → foreign defs

───────────────────────────────────────────────────────────────
  2. CONCEPTNET  →  test_conceptnet.py
───────────────────────────────────────────────────────────────
  WARUM: Reichste Relation-Datenbank. Mehrsprachig. Kein Key.
  KEY:   Keiner. Kostenlos.

  Run:
    python3 test_conceptnet.py
    python3 test_conceptnet.py --words mind truth --limit 200
    python3 test_conceptnet.py --langs en de fr

  Output:
    test_conceptnet_results.json

  Zeigt pro Wort:
    - Synonyme, Antonyme
    - is-a, part-of, causes, enables, implies
    - has-property, co-activated-with
    - DefinedAs (Kurzdefinitionen)
    - Fremdsprachäquivalente via TranslationOf

  ACHTUNG: Kann geblockt sein (403). Lokal testen.

───────────────────────────────────────────────────────────────
  3. DATAMUSE  →  test_datamuse.py
───────────────────────────────────────────────────────────────
  WARUM: Schnell, dicht, gute Synonyme/Antonyme/Trigger (EN)
  KEY:   Keiner. Kostenlos. Nur Englisch.

  Run:
    python3 test_datamuse.py
    python3 test_datamuse.py --words time mind truth
    python3 test_datamuse.py --diff   (Vergleich mit preseed.json)

  Output:
    test_datamuse_results.json

  Zeigt pro Wort:
    - Synonyme, Antonyme
    - Hypernyms (is-a), Hyponyms
    - Trigger (co-activated-with)
    - "Means like" (similar-to)
    - Adjektive für Nomen (has-property)
    --diff: was ist neu vs. existierendem preseed?

───────────────────────────────────────────────────────────────
  REIHENFOLGE EMPFOHLEN:
───────────────────────────────────────────────────────────────
  1. Google KG zuerst (Key holen, ausführen)
  2. Datamuse (kein Key, sofort)
  3. ConceptNet (kein Key, falls nicht geblockt)

  Dann jeweils Ergebnis-JSON oder Output zurück an Claude.

───────────────────────────────────────────────────────────────
  FEEDBACK-FORMAT (für Claude):
───────────────────────────────────────────────────────────────
  - JSON-Datei hochladen, oder
  - Konsolenoutput kopieren, oder
  - Spezifische Wörter/Probleme nennen

═══════════════════════════════════════════════════════════════
