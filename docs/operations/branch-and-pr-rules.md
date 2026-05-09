# Branch- und PR-Regeln (Greenfield)

> Konsolidierung aus **`Anweisungen.md`**, **`app/docs/greenfield/implementation/mvp/00-index.md`** (Sektion 2) und **`.cursor/rules/PR-WORKFLOW.mdc`**. Bei Konflikten gewinnen die genannten Kanon-Dateien — diese Seite ist der kurze Onboarding-Pfad.

---

## Branch-Namen

| Präfix      | Verwendung                           |
| ----------- | ------------------------------------ |
| `feature/`  | Neue Funktionalität (Default)        |
| `fix/`      | Bugfixes                             |
| `refactor/` | Struktur ohne neues Verhalten        |
| `test/`     | Reine Test-/Validierungs-Fixes       |
| `docs/`     | Nur Dokumentation                    |
| `chore/`    | Tooling, Dependencies, Konfiguration |

Slugs: kurz, **kebab-case**, keine Phasennummern im Namen (Zuordnung **`00-index.md`**).

---

## Issues

- Pro nicht-trivialem Schritt ein GitHub-Issue; trivial ≈ &lt; 30 Minuten, eine Datei, keine nennenswerte Test-Erweiterung.
- Issue-Titel = Slug ohne Branchpräfix (z. B. `event-log-schemas`).
- Labels: `phase:M0` … `phase:M8`, `tier:contract|impl|test|docs`, optional `risk:high`.

---

## Pull Requests

### Ein PR pro Index-Schritt (ab M1)

Ab Phase **M1** gilt als Standard:

1. **Änderungseinheit → Commit:** Jede zusammengehörige Änderung landet als **eigener, atomarer Commit** (ein Thema pro Commit; Squash auf `main` macht daraus einen Merge-Commit, aber der Branch soll **nicht** als „ein Riesendiff ohne Historie“ vor dem Öffnen der PR wachsen — entwickle und pushe in sinnvollen Häppchen).
2. **Commit nur über PR nach `main`:** Kein direkter Push auf **`main`**; jeder Commit liegt auf einem Branch (`feature/*`, `fix/*`, …) und geht nur per **PR** ein.
3. **Genau ein Plan-Schritt pro PR:** Eine PR erfüllt **genau einen** Eintrag **`Mn.k`** aus **`app/docs/greenfield/implementation/mvp/00-index.md`** (Slug/Branch-Spalte). Ausnahmen (**Bundle-PR**) nur, wenn **`orch`** / Index das ausdrücklich vorsieht und im PR-Body begründet ist.
4. **Nachweis:** PR-Body verlinkt oder nennt **`Mn.k`** und den **Slug**; mit dem Merge wird **`00-index.md`** auf **`[x]`**, **Datum** und **PR-Nummer** aktualisiert (vorzugsweise **in derselben PR**, nicht „still“ auf `main`).

**Hinweis:** Phase **M0** wurde teils **gebündelt** (historisch); ab **M1** gilt die 1:1-Regel **strikt**, außer dokumentierte Bundle-Ausnahme.

**PR-Titel:** konventionelles Präfix + Beschreibung, und sobald die PR existiert, endet die **erste Zeile der Commit-Message** mit **`(#NNN)`** (GitHub-PR-Nummer). Squash-Merge-Titel folgt derselben Regel.

**Pflicht-Abschnitte im PR-Body:**

1. **Summary** — Was und warum?
2. **Acceptance criteria** — Abnahme gegen Plan / Issue.
3. **Test plan** — Welche Kommandos / Checks sind grün?

**Squash-Merge** ist Default; linearer Verlauf soweit möglich.

---

## Cursor Co-authored-by Trailer

Wenn `Co-authored-by: Cursor <cursoragent@cursor.com>` in einer Message landet:

1. Lokal: **`python scripts/strip_cursor_coauthor_trailer.py .git/COMMIT_EDITMSG`** vor dem Commit, oder Pre-commit **`prepare-commit-msg`**-Hook installieren (`make bootstrap`).
2. Bereits gepusht: interaktives Rebase / amend nur nach Absprache; vermeide Noise auf **`main`**.

---

## Protected Deletions

Pfade unter **`NO-SILENT-DELETIONS.mdc`** dürfen nur mit Freigabe gelöscht werden:

- Commit-Body-Zeile `approved_deletions: path1 path2 …`, oder
- Eintrag in **`.agent-os/pr-spec.json`** unter `approved_deletions`, oder
- explizite User-Freigabe laut Regelwerk **plus** Nachweis im PR.

---

## Branch Protection (GitHub UI)

Empfohlene Required Checks für **`main`** (nach **`ci.yml`**): **`lint`**, **`type-check`**, **`test`**, **`schema-lint`**, **`protected-deletions`**, **`secrets-lint`**, **`pre-commit-ci`**, **`compose-smoke`**.
Squash-Merge, Reviews ≥ 1 — Details nach Team-Größe anpassen.

---

## Verwandte Pfade

- **`CLAUDE.md`**, **`Anweisungen.md`**, **`CONTRIBUTING.md`**
- **`app/docs/greenfield/implementation/mvp/00-index.md`**
- **`.cursor/rules/PR-WORKFLOW.mdc`**, **`NO-SILENT-DELETIONS.mdc`**
