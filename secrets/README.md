# Secrets (SOPS / AGE)

| Datei | Zweck |
|-------|--------|
| `.sops.yaml` | `creation_rules` + Age-Recipient für YAML unter `secrets/*.yaml`. |
| `hub.sops.yaml` | Verschlüsselte Hub-Secrets (Beispiel-Felder — **vor Produktion rotieren**). Erwartete Key-Namen für R2/Litestream sind in **`docs/operations/r2-buckets.md`** beschrieben (M1.9). |
| `example-age-devONLY.age.key` | **Nur Greenfield-Template:** Private Age-Identity zum Entschlüsseln der Beispieldatei. **Niemals produktive Geheimnisse mit diesem Key verschlüsseln.** |

## Lokales Entschlüsseln

Voraussetzung: [`sops`](https://github.com/getsops/sops) installiert.

```bash
export SOPS_AGE_KEY_FILE=secrets/example-age-devONLY.age.key
sops decrypt secrets/hub.sops.yaml > secrets/hub.env   # hub.env ist gitignored
```

Siehe **`docs/operations/secrets.md`** für Rotation und neue Recipients.
