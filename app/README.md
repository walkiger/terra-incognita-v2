# `app/` — neuer Produkt- und Implementierungs­root

> **Zweck.** Hier startet die aufgeräumte Neu‑Ausrichtung: Dokumentation,
> später gemeinsame Pakete und Multi‑Surface‑Clients (Web, Desktop,
> iOS/Android). Der frühere Monolith liegt bei Bedarf **lokal** unter
> **`archive/legacy-terra/`** (nicht im Git‑Snapshot — siehe Root‑**`README.md`**)
> und dient nur als **Referenz** beim Neubau; Portierung erfolgt durch neue
> Dateien unter **`app/`**, nicht durch Pflege des Archivs.

## Was liegt wo

| Pfad | Inhalt |
|------|--------|
| [`docs/greenfield/`](docs/greenfield/README.md) | MVP‑bis‑v2.0‑Plan, Architektur, Protokolle, Runbooks, ADRs, Formel‑Registry |
| [`backend/`](backend/) | Stub (M0.1); später Hub‑FastAPI (M5+) |
| [`engine/`](engine/) | Stub (M0.1); später lokales Engine‑Paket (M3+) |
| [`packages/`](packages/) | Stub (M0.1); später geteilte Typen, API‑Clients, Engine‑Interfaces |
| [`web/`](web/) | Stub (M0.1); später Vite/React‑Web‑Shell |
| *(folgt)* `mobile/` | später Expo/React‑Native oder natives Thin‑Client |

## Leseeinstieg

1. [`docs/greenfield/README.md`](docs/greenfield/README.md)
2. [`docs/greenfield/architecture/truth-anchors-and-ghosts.md`](docs/greenfield/architecture/truth-anchors-and-ghosts.md) — Truth Anchors, Geister aus Seeds, API‑Growth
3. Rest wie in der Greenfield‑Lesereihenfolge beschrieben

## Legacy

Kein `backend/` / `frontend/` mehr am Repository‑Root — nur Greenfield unter **`app/`** plus geteilte Docs. Frozen‑Baseline‑Pfade gelten **lokal** unter **`archive/`**, wenn du sie bereitstellst; Änderungen am Produktcode erfolgen im neuen Baum. Keine stillen Löschungen geschützter Projektpfade — siehe Projektregeln und Gates.
