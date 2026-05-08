# ADR-003 — mTLS für Engine-Hub-Verbindung

* **Status:** Accepted
* **Datum:** 2026-05-08
* **Bezug:** `architecture/security.md`, `protocols/event-log.md`,
  `implementation/mvp/M2-engine-protocol.md`

## Context

Die Engine läuft beim User lokal und verbindet sich per
WebSocket zum Hub, um Encounters/Tier-Events zu liefern und
Snapshots hochzuladen. Diese Verbindung trägt **alle** privaten
Daten des Users in Echtzeit. Sie muss:

* den Hub authentifizieren (User darf sicher sein, dass er nicht
  einen Man-in-the-middle bedient).
* die Engine authentifizieren (Hub darf sicher sein, dass nur
  registrierte Engines schreiben).
* gegen Spoofing-Angriffe robust sein, in denen ein Angreifer ein
  geleaktes JWT-Cookie verwendet.

## Decision

Wir setzen **mTLS** zusätzlich zur normalen Bearer-Auth:

* **Engine-CA**: self-signed, Schlüssel offline (Yubikey/USB),
  Empfänger-Liste unter SOPS.
* **Pro Engine**: ECDSA-P-256-Schlüssel + Cert mit
  CN=`engine_id`, `subjectAltName=URI:terra:engine:<engine_id>`.
* **Hub validiert**:
  * Cert-Chain bis Engine-CA,
  * `engine_registrations.cert_thumbprint`-Match,
  * `engine_registrations.is_active=1`,
  * Bearer-Token (Access-JWT mit `scope=engine`).
* Cloudflare-Tunnel-Edge wird so konfiguriert, dass die mTLS-Validation
  am Ursprung (Hub-Caddy) erfolgt — Cloudflare leitet das
  Client-Cert via `CF-Client-Cert`-Header durch.

## Consequences

* **Positiv:**
  * Defense-in-depth: ein geleaktes JWT alleine reicht nicht.
  * Engine-Identität ist kryptografisch nachweisbar (auch in
    `engine_signature` jedes Events).
  * Repudiation-Schutz (siehe `architecture/security.md` §2.3).
* **Negativ:**
  * Onboarding-Komplexität: User braucht
    Cert+Key-Material lokal. Mitigation: `terra-engine enroll`-CLI
    automatisiert den Vorgang.
  * Cert-Rotation muss aktiv betrieben werden (365 d; siehe
    `runbooks/operations.md` §9.3).
* **Neutral:**
  * Die Engine-CA bleibt Self-Signed; eine externe CA wäre
    Overkill für die ~25 erwarteten Engine-Endpunkte.

## Alternatives Considered

* **Bearer-only**: Verworfen — siehe Threat T-S-01 in
  `architecture/security.md` §2.1.
* **HMAC-Pre-Shared-Key**: einfach zu implementieren, aber
  Schlüssel­rotation komplex; keine asymmetrische Eigenschaft, die
  Repudiation verhindert.
* **OAuth-Device-Flow**: würde User bei jedem Engine-Start zum
  Browser zwingen; UX-Bruch im offline-fähigen Engine-Workflow.

## References

* `architecture/security.md` §3.4, §4
* `protocols/snapshot.md` §5.5
* `protocols/event-log.md` §3 (`engine_signature`)

---

*Greenfield-Initial-ADR.*
