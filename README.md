# terra-incognita-v2

Greenfield-Neustart für das Thin-Shell-MVP: Planung und Produktcode unter **`app/`**. Dieses Repository enthält **bewusst keine** Legacy-Codebasis aus dem Monolith; Referenzmaterial liegt bei Bedarf nur **lokal** oder im gesonderten Repo **`walkiger/terra-incognita`**.

## Einstieg

| Thema | Pfad |
|--------|------|
| Produkt-Root | [`app/README.md`](app/README.md) |
| Greenfield-Plan | [`app/docs/greenfield/README.md`](app/docs/greenfield/README.md) |
| Preseed-Daten | [`knowledge/README.md`](knowledge/README.md) |
| PDF-/Extraktions-Korpus (JSON) | [`research/README.md`](research/README.md) |
| Projektgedächtnis / Archive | [`memory/README.md`](memory/README.md) |
| Mitwirkung | [`CONTRIBUTING.md`](CONTRIBUTING.md) |

## Tests

```text
# Install uv: https://docs.astral.sh/uv/getting-started/installation/
uv sync --extra dev
uv run pytest tests -q -m "not compose_hub and not compose_vault"
```

Integration (Compose): **`uv run pytest tests/integration -q -m "compose_hub or compose_vault"`** (oder CI-Job **`compose-smoke`**).

Alternativ: **`make bootstrap`** dann **`make test`** (GNU Make; ruft `uv` auf).

CI synchronisiert mit **`uv sync --frozen --extra dev`** und führt Lint, Format-Check, **mypy** und **pytest** aus (**ohne** die Docker‑Compose‑Smoke‑Marker **`compose_hub`** / **`compose_vault`**). Der Job **`compose-smoke`** baut Hub‑ und Vault‑Stacks (**`deploy/compose/`**) und führt die zugehörigen Integrationstests aus.
