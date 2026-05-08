# Anweisungen.md — Regelwerk
> Lebendiges Dokument. Kategorisiert. Immer aktuell halten.
> Ergänzen bei jeder Session wenn neue Regeln entstehen.
> Diese Datei hat Vorrang vor allen anderen bei Konflikten.

---

## 1. Projektphilosophie

**Kernthese:** Intelligenz wird gewachsen, nicht gebaut.

Das System lernt durch echte Begegnungen. Nichts wird donated.
Jedes Konzept ist auf einen Encounter zurückführbar — Provenance ist heilig.

**Nicht verhandelbar:**
- Keine vorgefertigten Embeddings, kein Transfer-Learning
- Keine Konzepte ohne Herkunft
- Das System entwickelt Identität selbst — nie zugewiesen

---

## 2. Coding-Standards

### Allgemein
- **Python 3.12** — keine älteren Versionen
- **Type hints** — überall, keine Ausnahmen
- **Dataclasses** für alle Datenstrukturen
- **async/await** für I/O — niemals blocking calls im Tick-Loop
- Keine globalen Singletons — alles über `SystemState` übergeben

### Benennung
- Funktionen: `snake_case`
- Klassen: `PascalCase`
- Konstanten: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`
- Typo aus HTML **korrigieren**: `synaptcPrune` → `synaptic_prune`

### Docstrings
```python
def lnn_step(word: str | None, scale: float, state: SystemState) -> None:
    """
    Einziger Einstiegspunkt für LNN-Stimulation. Niemals lnn.step() direkt.

    Args:
        word:  KG-Wort für semantischen Input. None = Rausch-Schritt.
        scale: Skalierungsfaktor (0.003 = Hintergrund, 2.0 = Encounter).
        state: SystemState mit lnn, kg, tier_registry.

    Notes:
        Nach Tier-Emergenz ist lnn.iD > 32. Direkter Aufruf mit wv(w,32)
        würde nur T0-Kanal treiben — höhere Kanäle erhalten 0.
        build_lnn_input() baut den korrekten Multi-Tier-Vektor.
    """
```

Docstrings: **immer**. Kurz wenn offensichtlich, ausführlich wenn komplex.
Jede nicht-triviale Entscheidung im Docstring begründen.

### Imports
```python
# Standard library zuerst
import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

# Third-party
import numpy as np
import duckdb

# Lokale Imports
from backend.core.state import SystemState
from backend.core.kg import KnowledgeGraph
```

---

## 3. Dokumentations-Standards

### Pflichtdokumente pro Implementierung
Jedes Feature/Modul bekommt eine eigene `Implementierung.{name}.md`:

```
Implementierung.backend.api.md     ← REST + WebSocket
Implementierung.backend.core.lnn.md
Implementierung.backend.core.ebm.md
Implementierung.backend.core.kg.md
Implementierung.backend.db.md
Implementierung.frontend.md
...
```

### Struktur jeder Implementierungs-Datei
```markdown
# Implementierung.{name}.md

> Status: [ ] Geplant | [ ] In Arbeit | [x] Erledigt

## Zweck
1-3 Sätze was dieses Modul macht.

## Abhängigkeiten
Was muss vorher fertig sein?

## Geplante Funktionen / Endpoints
| Name | Signatur | Status | Tests |
|------|----------|--------|-------|
| ... | ... | Offen | T1, T2 |

## Tests
- T1: ...
- T2: ...

## Offene Fragen
- ...

## Erledigte Änderungen
- [Datum] Was wurde implementiert / geändert
```

### Wann updaten
- **Vor** der Implementierung: Planung + Tests eintragen
- **Während**: Status-Updates
- **Nach**: Erledigte Änderungen + was sich geändert hat
- **Bei Bugs**: Findings dokumentieren

### Implementierungen.Architektur.md
- Überblick über **alle** Implementierungen
- Status pro Komponente
- Öffnet automatisch neue Unterpunkte wenn nötig
- Einzige Datei die den Gesamtstatus zeigt

---

## 4. Test-Regeln

**Ausnahmslos: Kein Code ohne Tests.**

### Wann Tests schreiben
- **Vor** der Implementierung (TDD preferred)
- Mindestens parallel — niemals danach "vergessen"
- Jede Implementierungs-Datei hat Test-Sektion

### Test-Framework
```
pytest                    ← alle Tests
pytest-asyncio            ← async Tests
pytest-cov                ← Coverage
```

### Test-Benennung
```python
def test_lnn_step_with_noise_at_correct_dims():
    """Rausch-Schritt muss korrekte Input-Dimension haben."""
    ...

def test_ebm_wells_never_deleted():
    """Invariante: EBM_WELLS.delete() darf nie aufgerufen werden."""
    ...
```

### Was immer getestet wird
- Invarianten (die Non‑Negotiables in §7 sowie die Architektur‑Invarianten in `docs/ARCHITECTURE.md`)
- Happy path
- Edge cases (leere KG, 0 Nodes, None-Inputs)
- Performance-kritische Pfade (< 120ms pro Tick)

### Teststatus
Tests müssen grün sein bevor:
- Version-Nummer erhöht wird
- Auf `main` gemergt wird
- Als "erledigt" markiert wird

---

## 5. Git-Regeln

### Commit-Format (ausnahmslos)
```
[type] scope: beschreibung (#NNN)

Typen:
  [feat]     neue Funktion
  [fix]      Bugfix
  [docs]     Dokumentation
  [test]     Tests
  [refactor] kein neues Feature, kein Bug
  [chore]    Dependencies, Config
  [perf]     Performance

**Pflicht (PR-gekoppelt):** In der **ersten Zeile (Subject)** muss die **GitHub‑Pull‑Request‑Nummer** am Ende als **`(#NNN)`** stehen (`NNN` = Nummer des PR auf github.com — umgangssprachlich „PR #NNN“, technisch genau **diese** Klammer‑`#`‑Schreibweise wie bei GitHub‑Autolinks). Gleiches gilt bei **Squash‑Merge** für den Squash‑Betreff.  
**Referenz (Repo-Historie):** `9f638f5` — `fix: stabilize runtime contracts (#2)`.

Konventionell-Prefix‑Varianten (wie in Cursor‑Rules) ebenfalls mit Suffix: `feat: kurz (#NNN)`.

**Hinweis `terra-XXX`:** Session-/Plan-Tags wie `(terra-043)` können **zusätzlich** im Body oder in separaten Commits vorkommen; die **PR-Zuordnung** im Subject folgt trotzdem **`(#NNN)`** sobald die PR existiert (siehe Pflicht oben).

Wenn beim ersten Commit noch keine PR‑Nummer existiert: zeitnah **Draft‑PR** anlegen und danach Commits **`--amend`** / Folge‑Commits mit korrektem `(#NNN)` führen, oder vor Merge Squash‑Titel anpassen.

Beispiele:
  [feat] core/lnn: CfC step equation implementiert (#42)
  [fix]  core/kg: NaN guard in pause formula (#42)
  [test] core/ebm: T19-T22 Hopfield energy tests (#43)
  [docs] Implementierung.backend.api.md: endpoints geplant (#44)
```

### Cursor IDE / Agent — keine Co-authored-by Trailer

Wenn der **Cursor-Agent** `git commit` im integrierten Terminal ausführt, kann der Client automatisch eine Zeile **`Co-authored-by: Cursor <cursoragent@cursor.com>`** anhängen. Das ist **kein** Repo-Hook und gehört **nicht** in unsere Historie.

- **Empfohlen:** In Cursor **Settings → Agent → Attribution** die **Commit-Attribution** deaktivieren (für reine Git-Nutzung ohne diesen Trailer).
- **Zusätzlich (lokal):** Nach `pre-commit install` auch **`pre-commit install --hook-type prepare-commit-msg`** ausführen — der Hook ruft `scripts/strip_cursor_coauthor_trailer.py` auf und entfernt genau diesen Trailer aus der Message, falls er trotzdem anliegt (siehe `.pre-commit-config.yaml`).
- **Einmalige Historie bereinigen:** `py scripts/rewrite_branch_strip_cursor_coauthor.py <merge-base>` (Details: `memory/system/constraints.md`).

### Jede Änderung = ein Commit
Kein Bundling. Nie.

### Effiziente Ausführung (gleiche Regel, weniger Roundtrips)
Pro Änderung bleibt **genau ein Commit** mit einem eigenen Subject **`(#NNN)`**. Zur Einsparung von Shell-/Chat-Roundtrips darf der Parent-Agent die Schritte pro Commit in **einem** Terminal-Aufruf ausführen (z. B. PowerShell-Schleife: `git add <eine Datei>; git commit -m \"… (#NNN)\"` wiederholt; bei `ExitCode != 0` sofort abbrechen). Verboten bleibt: mehrere logische Änderungen oder mehrere Dateien in **einem** Commit.

### Branches
```
main        ← nur stable (tests grün, -stable label)
dev         ← laufende Entwicklung
feature/*   ← einzelne Features
```

### Versionsschema
```
MAJOR.FEATURE.FIX[-LABEL]

0 = in Entwicklung
1 = production-ready, keine bekannten Bugs

FEATURE: xxx — bei abgeschlossenem Feature + grüne Tests
FIX: yyy    — bei Bugfix, fortlaufend, nie zurückgesetzt

Labels: -alpha -beta -stable -broken
```

---

## 6. Session-Ablauf

**Jede Session beginnt mit:**
1. `python3 knowledge/verify.py` ausführen
2. `catchup.md` lesen — was war der letzte Stand?
3. `Implementierungen.Architektur.md` checken — was ist als nächstes?
4. Relevante `Implementierung.{name}.md` lesen
5. Dann erst Code schreiben

**Jede Session endet mit:**
1. Tests grün
2. `catchup.md` updaten
3. `Implementierungen.Architektur.md` updaten
4. Alle `Implementierung.{name}.md` updaten
5. Commit + Push

**Keine Session ohne:**
- Dokumentation update
- Test update
- Commit

---

## 7. Non-Negotiables (Architektur)

Canonical zusammengefasst — ergänzend `docs/ARCHITECTURE.md` und die jeweiligen `Implementierung.*.md`:

### LNN
- `lnn_step()` ist der **einzige** Einstiegspunkt für LNN-Stimulation
- `lnn.grow()` feuert **nur** aus `_on_tier_stable()`
- `build_lnn_input()` baut Multi-Tier-Vektor — nie direktes wv()
- **hD = iD immer** — Hidden State und Input Space wachsen synchron
- **Startdim = B = 256** (konfigurierbar) — nicht 32
- **Wachstumsformel:** `dim(N) = B × (1 + N×(N+1)/2)`
- T0 (Attraktor) ist Startpunkt: LNN entsteht erst bei erstem Attraktor
- T0 triggert LNN-Geburt auf 256 dims, aber kein weiteres Wachstum

### EBM / Tiers
- `ebm.wells` — **niemals** `.pop()/.clear()/del` — nur `make_dormant()`
- Member-Sets sind **immutable** nach Geburt (`frozenset`)
- `find_energy_wells()` ist die **einzige und universelle** Tier-Detection-Funktion
  - Gilt für T0→TN, keine separaten Funktionen pro Tier
  - Offenes Ende: T4, T5, T6+ entstehen durch dieselbe Logik
- Stop-Words werden **niemals** T1+ Members (außer `lift_tier_exclusion()`)

### Config / Locale
- **Nichts hardcoded** außer in `settings.py` und `locale.py`
- Alle numerischen Start-Parameter in `settings.py` (via `lnn_B`, `tick_hz`, etc.)
- Alle Labels/Namen in `locale.py` — Tier-Namen, UI-Text, Op-Labels
- Locale wird **vor dem Boot** gesetzt — nie zur Laufzeit wechseln

### Code
- Keine module-level Side-Effects — alles in `startup()`
- `FILTER.active()` — self-contained, keine externe Delegation
- Session-Start-Event — **genau einmal** pro Boot
- Typo-Confidence — immer `'low'`, nie höher

### Dokumentation
- Kein Code ohne Tests — **ausnahmslos**
- Keine Session ohne Dokumentation-Update
- Jede Abweichung von Empfehlungen — per Commit begründen

---

## 8. Living Document Policy

**Gilt für alle Dokumente in diesem Projekt:**

Alle Schemas, Implementierungen, Pläne und Empfehlungen sind
Ausgangspunkte — keine unveränderlichen Spezifikationen.

Erlaubt ist:
- Erweitern wenn neue Anforderungen entstehen
- Anpassen wenn die Realität es erfordert
- Überschreiben wenn bessere Lösungen gefunden werden
- Neue Kategorien hinzufügen wenn nötig

Pflicht bei jeder Änderung:
- Per Commit dokumentieren
- Begründung im Commit-Message
- Betroffene Docs updaten

---

## 9. Offene Entscheidungen (Sammlung)

> Hier landen Fragen die noch nicht entschieden sind.
> Bei Entscheidung: hierher und in relevantes Implementierungs-Doc.

- [ ] Erste öffentliche URL — Cloudflare Subdomain oder eigene Domain?
- [ ] Multi-User Rate-Limiting — pro IP oder per Auth-Token?
- [ ] LDV Expansion jenseits 2237 Wörter — wann und wie?
- [ ] T4+ Tier-Farben-Formel — `tier_color(N)` noch offen (generativ?)
- [ ] REM-Alternation im Dreaming — monotone Tiefe oder Zyklen?
- [ ] Snapshot-Interval — default 10min konfigurierbar — aber wie granular?
- [ ] MLX-Migration-Trigger — automatisch wenn T5 erreicht, oder manuell?
- [ ] Locale zur Laufzeit wechselbar? (aktuell: nur pre-boot)

---

## 10. Locale + Config — Übersicht

Alle konfigurierbaren Parameter werden **vor dem Boot** gesetzt.
Das ermöglicht vollständige UI-Ausrichtung auf den User.

### Was lokalisierbar ist
```python
# backend/config/locale.py
{
  "lang": "de" | "en" | "fr" | ...,
  "tier_names": {0: "...", 1: "...", 2: "...", 3: "..."},
  "op_labels": {
    "resting":    "ruhend",
    "receiving":  "empfangend",
    "responding": "antwortend",
    "initiating": "initiierend",
    "babbling":   "murmelnd",
    "dreaming":   "träumend",
  },
  "system_labels": {
    "boot":     "Booten",
    "encounter": "Begegnung",
    ...
  }
}
```

### Was numerisch konfigurierbar ist
```python
# backend/config/settings.py (Auswahl)
lnn_B              = 256      # Basis-Einheit für LNN-Dimensionen
tick_hz            = 8        # systemTick Frequenz
kg_node_limit      = 16_000   # Start-Kapazität KG
ebm_theta          = 0.18     # EBM Schwellenwert
ebm_tick_cadence   = 4        # EBM alle N systemTicks
well_grace_s       = 5_400    # 90 Minuten Well-Schutz
```

*Details: `Implementierung.backend.locale.md`*
