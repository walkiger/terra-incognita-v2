# Hub VM (Oracle VM1) — Cloudflare-Tunnel, Compose und Status

> **Zweck.** Schrittfolge für den **Hub** auf der ersten Oracle-VM (`terra-hub-01`), Ausrichtung an **`deploy/cloudflared/`** und **`deploy/compose/hub.yml`**.
> **Stand:** 2026-05-09 — wird bei Änderungen am Ist-Zustand aktualisiert.

---

## 1. Ist-Zustand (Checkpoint — bei Meilensteinen §6 spiegeln)

| Thema                                                            | Status                | Kurznotiz                                                                                                                                                               |
| ---------------------------------------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Oracle Compute **`terra-hub-01`**                                | erledigt              | Shape **`VM.Standard.E2.1.Micro`**, Region **`eu-frankfurt-1`**, Ubuntu **24.04 Minimal**, User **`ubuntu`**.                                                           |
| Öffentliche IPv4                                                 | vorhanden             | Ephemeral — bei Änderung der Zuweisung neue IP in der OCI-Konsole prüfen.                                                                                               |
| Docker Engine + Compose Plugin                                   | erledigt              | Manuelle Installation nach Cloud-init-YAML-Fehler (Unicode); **`docker run hello-world`** erfolgreich (**amd64**).                                                      |
| Cloud-init User Data                                             | fehlgeschlagen / egal | Log: YAML konnte nicht gemerged werden („unacceptable character” — typisch Umlaute/Sonderzeichen im eingefügten Text). Docker wurde nicht durch Cloud-init installiert. |
| GitHub SSH-Zugriff für Clone                                     | erledigt              | **`ssh -T git@github.com`** erfolgreich; Repo **`terra-incognita-v2`** auf der VM geklont.                                                                              |
| **Domain**                                                       | erledigt              | **`terra-incognita.cloud`** bei checkdomain.de (~1 €/Jahr), Cloudflare Free zone, NS **`melissa`**/**`santino`**`.ns.cloudflare.com`. Hub-FQDN: **`hub.terra-incognita.cloud`**. |
| Cloudflare Tunnel **`terra-hub`**                                | erledigt (Modus B)    | Tunnel-UUID **`8d4bb120-c82e-4344-be09-73fa4b012c74`**, systemd-Token, 4 Connections (Frankfurt). Published Route + CNAME (proxied) auf **`hub.terra-incognita.cloud`**. |
| **`docker compose … hub`** + erreichbarer Origin für Host-Tunnel | erledigt              | **`hub.override.dev.yml`** (Port **8080**) + **`hub.override.host-tunnel.yml`**. Lokal **`curl http://127.0.0.1:8080/v1/health`** → **200**.                             |
| Smoke **`https://hub.terra-incognita.cloud/v1/health`** extern   | wartend               | Wartet auf NS-Propagierung (checkdomain.de → Cloudflare). Danach erster externer Smoke.                                                                                 |
| Zweite VM (Vault)                                                | offen                 | Separater Tunnel + **`vault.yml`** (nicht Teil dieser Seite).                                                                                                           |

---

## 2. Architektur — zwei gültige Betriebsmodi

**Compose (`deploy/compose/hub.yml`)** startet u. a. **`api`** (FastAPI Stub), **`caddy`**, **`cloudflared`** (Profil **`minimal`** / **`default`**).

### Gemeinsame Bausteine

- **`deploy/caddy/Caddyfile.hub`:** nur **`/v1*`** wird an **`api:8000`** durchgereicht — **`GET /v1/health`** gehört dazu.
- **`deploy/cloudflared/config.hub.yml`:** Ingress nur für **Modus A** (Tunnel **im** Container mit Credential-JSON).

### Modus A — Tunnel im Docker-Netz (Repo-„klassisch“)

- **`deploy/cloudflared/credentials/<TUNNEL_UUID>.json`** auf der VM; **`config.hub.yml`** mit echter UUID und Hostnames.
- Der **`cloudflared`-Container** spricht Origins **`http://api:8000`** / **`http://caddy:80`** direkt im Compose-Netz.
- **Kein** Host-Port **8080** nötig, solange du nicht manuell auf der VM gegen Caddy testen willst — für Produktion aber **`hub.override.dev.yml`** trotzdem sinnvoll für lokale Smoke-Tests.

### Modus B — Tunnel auf dem Host (Zero Trust UI + Token + `systemd`)

- Im Dashboard: Tunnel anlegen → **Linux** installieren → **`sudo cloudflared service install <TOKEN>`**.
- **Public Hostnames** im Tunnel: öffentlicher Hostname (z. B. **`terra-incognita.is-into.tech`**) → Service **`http://127.0.0.1:8080`** (**HTTP**, nicht `https://` zum localhost).
- **Pflicht:** **`hub.override.dev.yml`** published Caddy auf **`127.0.0.1:8080`** — sonst ist auf der VM **nichts** auf **8080** und Cloudflare liefert u. a. **HTTP 530**, lokal **`curl: (7) Failed to connect`**.
- **Kein zweiter Connector:** Parallel dürfen **nicht** Host-`cloudflared` **und** der echte **`cloudflared`-Container** denselben Tunnel bedienen. Mit Host-Tunnel zusätzlich **`deploy/compose/hub.override.host-tunnel.yml`** verwenden — stubbt den Container wie CI (**Alpine `sleep`**).

### DNS ohne Cloudflare-Zone

Wenn die Domain **nicht** als Zone in Cloudflare liegt (z. B. nur DNS bei **is-into.tech**): **`cloudflared tunnel route dns`** entfällt oder scheitert — stattdessen **CNAME** vom gewünschten Hostnamen auf **`<TUNNEL_UUID>.cfargotunnel.com`** beim DNS-Provider setzen. Tunnel und Connector funktionieren trotzdem.

**Wichtig:** Eine Zone bei Cloudflare ist **nicht** nötig, um im Tunnel einen **Public Hostname** (FQDN → Origin-URL) anzulegen — nur für automatisch angelegte DNS-Einträge. **Ohne** diesen Public-Hostname-Eintrag ist die Route für den FQDN leer.

---

## 3. Cloudflare Tunnel — Schritte nach Modus

### 3.1 `cloudflared` auf der Hub-VM installieren (AMD64 / E2 Micro)

**Variante Paket-Repo** (wie Zero-Trust-Wizard „Linux“):

```bash
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt-get update && sudo apt-get install -y cloudflared
cloudflared version
```

**Variante `.deb` direkt:**

```bash
curl -fsSL -o /tmp/cloudflared-linux-amd64.deb \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo apt-get install -y /tmp/cloudflared-linux-amd64.deb
cloudflared version
```

### 3.2 Modus B — Dashboard + systemd (ohne `cloudflared login` auf der Zone)

1. Zero Trust → **Networks** → **Tunnels** → Tunnel erstellen (z. B. **`terra-hub`**).
2. **Install connector** → OS **Linux** → Token kopieren.
3. Auf der VM: **`sudo cloudflared service install <TOKEN>`** → Dienst aktiv (**`systemctl enable --now cloudflared`** falls nicht automatisch).
4. Im Tunnel **Published Application Routes** (**Pflicht**, sonst extern **HTTP 530** — siehe §5.2): exakt den öffentlichen **FQDN** eintragen (z. B. **`hub.terra-incognita.cloud`**) → Service **`http://127.0.0.1:8080`** (**HTTP**, kein `https://` zum localhost).
5. DNS beim Provider: **CNAME** → **`<TUNNEL_UUID>.cfargotunnel.com`** (UUID aus der Tunnel-Übersicht, nicht die „Replica ID“).

**Sicherheit:** Token wie ein Passwort behandeln; nicht ins Repo committen; bei Leak im Dashboard rotieren.

### 3.3 Modus A — CLI: Tunnel erzeugen, Credential, `config.hub.yml`

Voraussetzung: **`cloudflared login`** gelingt (liefert **`~/.cloudflared/cert.pem`**). Ohne Cloudflare-Zone schlägt die OAuth-Auswahl oft fehl — dann **Modus B** oder eine Zone/beigelgte Domain für Login klären.

```bash
cloudflared tunnel create hub-prod
cloudflared tunnel route dns hub-prod terra.example.tld
cloudflared tunnel route dns hub-prod app.terra.example.tld
```

(`hub-prod` ist der **Tunnel-Name**; bei anderem Namen anpassen. Bei DNS nur extern: Schritt **`route dns`** durch manuelles CNAME ersetzen.)

Credential auf die VM:

```bash
mkdir -p deploy/cloudflared/credentials
chmod 700 deploy/cloudflared/credentials
install -m 0600 /pfad/zur/<UUID>.json deploy/cloudflared/credentials/<UUID>.json
```

**`deploy/cloudflared/config.hub.yml`:** **`TUNNEL_ID`** und **`credentials-file`** auf dieselbe UUID setzen; Hostnames **`terra.example.tld`** / **`app.terra.example.tld`** durch produktive Namen ersetzen (`ingress` zeigt auf **`http://api:8000`** bzw. **`http://caddy:80`**).

---

## 4. Compose Hub — Befehle vom Repo-Root

### 4.1 Modus B (Host-Tunnel + Port 8080 für Cloudflare)

**Empfohlen**, wenn **`cloudflared`** als **`systemd`** läuft:

```bash
cd ~/terra-incognita-v2   # Pfad anpassen
docker compose \
  -f deploy/compose/hub.yml \
  -f deploy/compose/hub.override.dev.yml \
  -f deploy/compose/hub.override.host-tunnel.yml \
  --profile minimal \
  up -d --build
```

### 4.2 Modus A (Tunnel nur im Container)

```bash
docker compose \
  -f deploy/compose/hub.yml \
  -f deploy/compose/hub.override.dev.yml \
  --profile minimal \
  up -d --build
```

(Optional **`hub.override.host-tunnel.yml`** hier **nicht** verwenden — der echte **`cloudflared`-Container** soll den Tunnel halten.)

### 4.3 Lokaler Health-Check

```bash
curl -fsS http://127.0.0.1:8080/v1/health
```

Erwartung: HTTP **200** und JSON (Stub, z. B. Version **`0.0.1-bootstrap`**).

### 4.4 Logs

```bash
docker compose -f deploy/compose/hub.yml -f deploy/compose/hub.override.dev.yml -f deploy/compose/hub.override.host-tunnel.yml --profile minimal logs -f api caddy
# Bei Modus A ohne Host-Stubs zusätzlich cloudflared-Container-Logs prüfen.
journalctl -u cloudflared -f   # Host-Connector (Modus B)
```

---

## 5. Abnahme und Fehlerbilder

### 5.1 Extern

```text
https://hub.terra-incognita.cloud/v1/health   → 200, JSON
```

### 5.2 HTTP **530** trotz lokalem **`127.0.0.1:8080` → 200**

**Symptom:** `curl -fsSI https://<öffentlicher-host>/v1/health` liefert **HTTP 530** (auch **von der Hub-VM** aus); parallel `curl -fsS http://127.0.0.1:8080/v1/health` → **200** mit JSON.

**Typische Ursachen:** (a) Der Connector ist verbunden („Replica connected“), aber unter **Zero Trust → Tunnel → Public Hostnames** fehlt noch ein Eintrag für **genau diesen FQDN**. Der Edge weiß dann nicht, welche Origin-URL der Tunnel bedienen soll.

**Maßnahme:** Public Hostname **hinzufügen**: Hostname = voller öffentlicher Name (z. B. **`terra-incognita.is-into.tech`**) → Service **`http://127.0.0.1:8080`**. DNS weiter per **CNAME** auf **`<TUNNEL_UUID>.cfargotunnel.com`** beim Provider — **ohne** Cloudflare-Zone möglich.

**Verwechslung vermeiden:** Die **Tunnel-UUID** (für DNS/CNAME) ist **nicht** dieselbe wie eine **Replica-ID** in der Connector-Liste.

### 5.3 HTTP **530** von Cloudflare + lokaler **`Connection refused` auf :8080**

| Ursache                                   | Maßnahme                                                 |
| ----------------------------------------- | -------------------------------------------------------- |
| Compose ohne **`127.0.0.1:8080`-Mapping** | **`hub.override.dev.yml`** verwenden (§4).               |
| Stack nicht gestartet / Caddy unhealthy   | **`docker compose ps`**, Logs **`api`** / **`caddy`**.   |
| Public Hostname zeigt auf falschen Port   | Im Tunnel **Service** exakt **`http://127.0.0.1:8080`**. |

### 5.4 Free-Subdomain-Dienste und Cloudflare Tunnel

Free-Subdomain-Dienste (z. B. `is-into.tech` via is-pro.dev) sind mit eigenem Cloudflare Tunnel **inkompatibel**, wenn der Dienst selbst einen Cloudflare-Proxy davorschaltet. Der Traffic landet dann beim Cloudflare-Account des Domain-Besitzers, nicht beim eigenen Tunnel. **Proxy deaktivieren** hilft nicht: `cfargotunnel.com` hat ohne Cloudflare-Proxy keine A-Records.

**Empfehlung:** Eigene Domain (z. B. **`terra-incognita.cloud`**, ~1 EUR/Jahr) als Cloudflare Free zone. CNAME dort proxied anlegen.

### 5.5 Doppelter Tunnel-Connector

Symptome: instabile Replikas, unerwartete Fehler. **Nur einen** Connector pro Tunnel-ID — bei Host-Tunnel **`hub.override.host-tunnel.yml`** nutzen.

---

## 6. Checkliste (Pflege bei Meilensteinen)

| Nr  | Artefakt                                                     | Hinweis                                                                    |
| --- | ------------------------------------------------------------ | -------------------------------------------------------------------------- |
| 1   | Oracle Hub-VM                                                | Optional: Reserved Public IP für stabiles SSH.                             |
| 2   | Docker + Clone                                               | Regelmäßig **`git pull`** vor Deploys.                                     |
| 3   | **Modus B:** systemd **`cloudflared`** + Public Hostname     | **`http://127.0.0.1:8080`**; DNS **CNAME** zur Tunnel-UUID.                |
| 4   | **Modus A:** **`credentials/*.json`** + **`config.hub.yml`** | Rechte **0600**; UUID konsistent.                                          |
| 5   | Compose **`minimal`** + **`hub.override.dev.yml`**           | Fast immer für VM-Smoke; Modus B **+** **`hub.override.host-tunnel.yml`**. |
| 6   | **`curl http://127.0.0.1:8080/v1/health`**                   | Muss **vor** externem Test funktionieren.                                  |
| 7   | **`https://…/v1/health`** extern                             | Nach DNS-Propagierung.                                                     |
| 8   | Vault-VM + zweiter Tunnel                                    | Separates Playbook / **`config.vault.yml`**.                               |

---

## 7. Referenzen im Repo

| Dokument / Pfad                                                 | Inhalt                                           |
| --------------------------------------------------------------- | ------------------------------------------------ |
| **`deploy/README.md`**                                          | Compose-Profile, Ports, CI.                      |
| **`deploy/cloudflared/README.md`**                              | Tunnel-Modi, Credentials, Acceptance.            |
| **`deploy/compose/hub.override.dev.yml`**                       | Caddy → Host **8080**.                           |
| **`deploy/compose/hub.override.host-tunnel.yml`**               | Container-`cloudflared` stubben bei Host-Tunnel. |
| **`deploy/cloudflared/config.hub.yml`**                         | Ingress-Vorlage (**Modus A**).                   |
| **`app/docs/greenfield/implementation/mvp/M0-bootstrap.md`** §5 | Phasen-Gate Hub/Vault-Smokes.                    |

---

_Pflege:_ Bei jedem erreichten Meilenstein §1 und §6 aktualisieren sowie Datum im Kopf anpassen.
