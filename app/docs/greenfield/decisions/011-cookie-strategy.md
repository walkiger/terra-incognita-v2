# ADR-011 — Cookie-Strategie (`HttpOnly`, `SameSite=Strict`, `Secure`)

* **Status:** Accepted
* **Datum:** 2026-05-08
* **Bezug:** `architecture/security.md` §3.3,
  `protocols/auth-flow.md` §3.

## Context

Tokens müssen im Browser gespeichert werden. Drei Alternativen:

* **`localStorage`**: anfällig gegen XSS (jedes JS kann lesen).
* **`sessionStorage`**: gleich, mit kürzerem Lebenszyklus.
* **`HttpOnly`-Cookie**: nur server­seitig lesbar, robust gegen XSS.

CSRF wird durch `SameSite=Strict` auf modernen Browsern abgedeckt.

## Decision

* **Cookies, nicht localStorage.**
* **Flags:** `HttpOnly; Secure; SameSite=Strict`.
* **Path-Eingrenzung:** Refresh-Cookie auf `Path=/api/v1/auth`,
  Access-Cookie auf `Path=/`.
* **Domain:** `.terra.example` (apex + subdomains).
* **Max-Age:** Access 900, Refresh 2592000.
* **Frontend-CSP:** `script-src 'self'; object-src 'none'` —
  zusätzlich gegen XSS.

## Consequences

* **Positiv:**
  * XSS-Schutz: JS kann den Token-Inhalt nicht lesen.
  * CSRF-Schutz durch `SameSite=Strict`.
  * Path-Eingrenzung: nur Auth-Routen sehen das Refresh-Cookie.
* **Negativ:**
  * Client-seitige Logout-Visualisierung erfordert API-Round-Trip
    (kein lokales Cookie-Löschen ohne Server-Bestätigung).
* **Neutral:**
  * In v2.0 mit Multi-Domain-Setup (z.B. `app.terra.example` +
    `api.terra.example`) könnte `SameSite=Lax` notwendig werden;
    derzeit Single-Origin → Strict bleibt.

## Alternatives Considered

* **localStorage + Bearer im Header**: einfaches Schema, aber
  XSS-anfällig.
* **`SameSite=Lax`**: erlaubt cross-site Top-Level-GET, was bei
  reinen Subdomains nicht nötig ist.

## References

* RFC 6265bis (Cookies, SameSite)
* OWASP Top 10 (XSS, CSRF)
* `architecture/security.md` §3.3
* `protocols/auth-flow.md` §3

---

*Greenfield-Initial-ADR.*
