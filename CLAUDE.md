# CLAUDE.md — Orientierung (terra-incognita-v2)

> Kurzfassung für Sessions in diesem **Greenfield**-Repo (bewusst ohne Legacy-Tree).

---

## Repo und Zweck

**Repo:** https://github.com/walkiger/terra-incognita-v2  

**Inhalt:** Thin-Shell-MVP-Planung und späterer Produktcode unter **`app/`**. Kein geklonter Monolith-Stand aus **terra-incognita** — bei Bedarf dort oder lokal nachschlagen.

---

## Wo du anfängst

1. [`README.md`](README.md) — Überblick  
2. [`app/README.md`](app/README.md) — Produkt-Root  
3. [`app/docs/greenfield/README.md`](app/docs/greenfield/README.md) — Lesepfad MVP M0–M8  

Git-/Agent-Disziplin: **`Anweisungen.md`** und **`.cursor/rules/`**.

---

## Tests (heute)

```text
py -m pip install -r requirements-ci.txt
py -m pytest tests/test_repo_layout.py -q
```

Windows: siehe **`CONTRIBUTING.md`** (`py`, nicht `python3`).
