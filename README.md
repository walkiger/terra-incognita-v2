# terra-incognita-v2

Greenfield-Neustart für das Thin-Shell-MVP: Planung und Produktcode unter **`app/`**. Dieses Repository enthält **bewusst keine** Legacy-Codebasis aus dem Monolith; Referenzmaterial liegt bei Bedarf nur **lokal** oder im gesonderten Repo **`walkiger/terra-incognita`**.

> **Vor dem ersten Commit:** Lies **[`docs/operations/branch-and-pr-rules.md`](docs/operations/branch-and-pr-rules.md)** (Branches, PR-Pflichtsektionen, Commit **`(#NNN)`**, Protected Deletions).

## Einstieg

| Thema                          | Pfad                                                             |
| ------------------------------ | ---------------------------------------------------------------- |
| Produkt-Root                   | [`app/README.md`](app/README.md)                                 |
| Greenfield-Plan                | [`app/docs/greenfield/README.md`](app/docs/greenfield/README.md) |
| Preseed-Daten                  | [`knowledge/README.md`](knowledge/README.md)                     |
| PDF-/Extraktions-Korpus (JSON) | [`research/README.md`](research/README.md)                       |
| Projektgedächtnis / Archive    | [`memory/README.md`](memory/README.md)                           |
| Mitwirkung                     | [`CONTRIBUTING.md`](CONTRIBUTING.md)                             |

## Tests

```text
# Install uv: https://docs.astral.sh/uv/getting-started/installation/
uv sync --extra dev
uv run pytest tests -q -m "not compose_hub and not compose_vault and not compose_observability"
```

Integration (Compose): **`uv run pytest tests/integration -q -m "compose_hub or compose_vault or compose_observability"`** — oder den zusammengefassten **`compose-smoke`**-Workflow auf GitHub Actions.

Alternativ: **`make bootstrap`** dann **`make test`** (GNU Make; ruft `uv` auf).

CI nutzt **`uv sync --frozen --extra dev`** und mehrere Jobs (**`lint`**, **`type-check`**, **`test`** mit Coverage, **`schema-lint`**, **`protected-deletions`**, **`secrets-lint`**, **`pre-commit-ci`**, **`compose-smoke`**).
