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
4. [`memory/README.md`](memory/README.md) — Session-/System-Archive (Legacy‑Kontinuität zeigt auf **`walkiger/terra-incognita`**)
5. [`docs/operations/hub-oracle-vm1-deployment-status.md`](docs/operations/hub-oracle-vm1-deployment-status.md) — Hub auf Oracle-VM: Cloudflare Tunnel (**Modus Container vs. Host**); Domain **`terra-incognita.cloud`** (Cloudflare Free zone); Hub-FQDN **`hub.terra-incognita.cloud`**; **NS bei Cloudflare** = authoritative **DNS → Records** (Registrar-„Subdomain“ ohne CNAME zur Tunnel-UUID ersetzt das nicht); **Published application routes** / Zero-Trust-Hostnamen (**Pflicht**; sonst **HTTP 530** trotz lokalem Origin OK); ohne Cloudflare-Zone alternativ externer Provider-CNAME; Free-Subdomain-Fallen und Parking/Fehlzonen siehe §5.4–§5.6.
6. [`app/docs/greenfield/implementation/mvp/00-index.md`](app/docs/greenfield/implementation/mvp/00-index.md) **§7** und [`docs/operations/branch-and-pr-rules.md`](docs/operations/branch-and-pr-rules.md) — bei jedem abgeschlossenen **`Mn.k`**: Status-Tabelle **und** Phasendoku (**`M*n*-*.md`**, § Erledigte Änderungen) **in derselben PR**; bei Kommando-/Pfadänderungen zusätzlich **`CONTRIBUTING.md`** / diese **`CLAUDE.md`** / **`README.md`**.

Git-/Agent-Disziplin: **`Anweisungen.md`** und **`.cursor/rules/`**.

---

## Tests (heute)

```text
uv sync --extra dev
uv run pytest tests -q -m "not compose_hub and not compose_vault and not compose_observability and not alembic_isolation"
```

Voller Integration/Docker-Lauf (CI **`compose-smoke`**):
`uv run pytest tests/integration -q -m "compose_hub or compose_vault or compose_observability"`
Details und **ruff**: **`CONTRIBUTING.md`**. Ohne globales `uv`: `py -m pip install uv` und dann `py -m uv sync --extra dev`.

Windows: siehe **`CONTRIBUTING.md`** (`py`, nicht `python3`).
