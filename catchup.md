# catchup.md — Session- und Release-Log (terra-incognita-v2)

> Living document. Kurze, datierte Einträge; keine Romane.

---

## 2026-05-09 — Greenfield M0 abgeschlossen (`greenfield-M0`)

Thin-Shell-MVP **Phase M0** (Bootstrap & Tooling) ist im Repo **`walkiger/terra-incognita-v2`** umgesetzt (Lieferung **PR #10**, Branch **`feature/m0-bootstrap-m05-m010`**): Compose Hub/Vault inkl. Cloudflared-Konfig-Vorlagen, SOPS/AGE-Secrets-Stub, Pre-commit + erweiterte GitHub Actions (Lint, Mypy, Tests/Coverage, Schema-Lint, Protected-Deletions, Secrets-Layout, Pre-commit-CI, Compose-Smokes inkl. Prometheus/Grafana-Profil), Observability-Baseline, konsolidierte Branch-/PR-Doku (`docs/operations/branch-and-pr-rules.md`). VM-Gates laut **`M0-bootstrap.md`** §5 und Annotated Tag **`v0.1.0`** sind nach Merge manuell bzw. per Release-Schritt zu setzen (**`.agent-os/pr-spec.json`**).

---
