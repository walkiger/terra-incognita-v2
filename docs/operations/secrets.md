# Secrets-Betrieb (AGE + SOPS)

End-to-End-Anleitung für Entwickler und Operatoren — ergänzt **`secrets/README.md`**.

## Neuer Entwickler-Rechner

1. **`sops`** und **`age`** installieren (Distribution-/Vendor-Pakete).
2. Private Age-Key-Datei sicher übergeben (nicht per E-Mail-Klartext); Export z. B. aus 1Password / Vault.
3. `export SOPS_AGE_KEY_FILE=/pfad/zur/age.key`
4. `sops decrypt secrets/hub.sops.yaml > secrets/hub.env` (Ausgabe nie committen).

## Neuen Recipient hinzufügen

```bash
export SOPS_AGE_KEY_FILE=<bestehender-admin-key>
sops rotate -i secrets/hub.sops.yaml    # optional re-encrypt
# Recipient in secrets/.sops.yaml ergänzen, dann:
sops updatekeys secrets/hub.sops.yaml
```

## Recipient entfernen

Public Key aus **`secrets/.sops.yaml`** entfernen, dann **`sops updatekeys`** mit einem noch gültigen Admin-Key ausführen.

## Notfall-Rotation

1. Alle aktiven Secrets als kompromittiert behandeln.
2. Neue Age-Keys ausgeben; alte aus **`creation_rules`** löschen.
3. **`hub.sops.yaml`** mit neuen Werten neu verschlüsseln; Dienste neu deployen.
4. Incident in **`memory/system/decisions.md`** dokumentieren.

## Compose-Integration

**`make secrets-decrypt`** schreibt **`secrets/hub.env`**. Compose liest Variablen über `env_file` (in späteren Milestones verdrahtet); bis dahin manuell exportieren oder in Overrides einbinden.
