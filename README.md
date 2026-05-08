# terra-incognita-v2

Greenfield-Neustart für das Thin-Shell-MVP: Planung und Produktcode unter **`app/`**. Dieses Repository enthält **bewusst keine** Legacy-Codebasis aus dem Monolith; Referenzmaterial liegt bei Bedarf nur **lokal** oder im gesonderten Repo **`walkiger/terra-incognita`**.

## Einstieg

| Thema | Pfad |
|--------|------|
| Produkt-Root | [`app/README.md`](app/README.md) |
| Greenfield-Plan | [`app/docs/greenfield/README.md`](app/docs/greenfield/README.md) |
| Projektgedächtnis / Archive | [`memory/README.md`](memory/README.md) |
| Mitwirkung | [`CONTRIBUTING.md`](CONTRIBUTING.md) |

## Tests

```text
py -m pip install -r requirements-ci.txt
py -m pytest tests/test_repo_layout.py -q
```

CI (GitHub Actions) führt denselben Layout-Test aus.
