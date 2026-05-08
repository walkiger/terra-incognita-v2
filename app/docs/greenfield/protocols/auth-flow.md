# `protocols/auth-flow.md` — Auth-Flow (Login, Refresh, Logout)

> **Zweck.** Vollständige Spezifikation der Auth-Sequenzen für v1.0:
> Browser-Session-Login, Token-Rotation, Logout, Engine-Auth,
> Account-Sperre. Ergänzt `architecture/security.md` und
> `contracts/openapi-v1-summary.md`.
>
> **Geltung:** eingefroren ab v0.5.x (M5). Jede Bruch-Änderung erfordert
> Major-Bump (v2.0).

---

## Inhalt

1. [Akteure & Vertrauenszonen](#1-akteure--vertrauenszonen)
2. [Token-Modell](#2-token-modell)
3. [Cookie-Strategie](#3-cookie-strategie)
4. [Sequenz: Registrierung](#4-sequenz-registrierung)
5. [Sequenz: Login](#5-sequenz-login)
6. [Sequenz: Refresh](#6-sequenz-refresh)
7. [Sequenz: Logout](#7-sequenz-logout)
8. [Sequenz: Reuse-Detection](#8-sequenz-reuse-detection)
9. [Sequenz: Engine-Auth (mTLS + JWT)](#9-sequenz-engine-auth-mtls--jwt)
10. [Sequenz: Account-Sperre durch Admin](#10-sequenz-account-sperre-durch-admin)
11. [Sequenz: Passwort-Reset (v1.x ergänzt)](#11-sequenz-passwort-reset-v1x-ergänzt)
12. [Server-State pro Sequenz](#12-server-state-pro-sequenz)
13. [Test-Pflichten](#13-test-pflichten)

---

## 1. Akteure & Vertrauenszonen

* **Browser** — Frontend in Z0/Z1 (Cloudflare-Edge).
* **Engine-CLI** — User-Workstation, Z4.
* **Hub-FastAPI** — Z2.
* **Vault-VM** — Z3 (Read-Mirror, kein Auth-Pfad).

---

## 2. Token-Modell

| Token            | TTL     | Speicherort           | Rotation       | Revoke               |
|------------------|---------|------------------------|----------------|-----------------------|
| Access-JWT       | 15 min  | `HttpOnly`-Cookie      | bei Refresh    | natürlich (TTL)       |
| Refresh-JWT      | 30 d    | `HttpOnly`-Cookie      | bei Refresh    | DB-`revoked=1`        |
| Engine-Cert      | 365 d   | Datei beim User        | manuell (Admin) | Cert-Thumbprint deaktiv |
| MFA-TOTP-Seed (v1.x) | n/a | DB                  | n/a             | gelöscht bei Disable  |

**Claims (Access-JWT):**

```json
{
  "sub": 42,
  "role": "user",
  "lang": "de",
  "iat": 1714900000,
  "exp": 1714900900,
  "kid": "k-2026-05",
  "aud": "terra-mvp",
  "iss": "https://terra.example",
  "scope": "user"
}
```

**Claims (Refresh-JWT):**

```json
{
  "sub": 42,
  "iat": 1714900000,
  "exp": 1717492000,
  "kid": "k-2026-05",
  "aud": "terra-mvp:refresh",
  "iss": "https://terra.example",
  "family_id": "fam_abc"
}
```

---

## 3. Cookie-Strategie

```
Set-Cookie: access_token=<jwt>; HttpOnly; Secure; SameSite=Strict; Path=/; Domain=.terra.example; Max-Age=900
Set-Cookie: refresh_token=<jwt>; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth; Domain=.terra.example; Max-Age=2592000
```

* **Access** ist auf `Path=/` gemappt — alle API-Routen erhalten
  ihn automatisch.
* **Refresh** ist auf `Path=/api/v1/auth` eingeschränkt — keine
  andere Route bekommt ihn je zu Gesicht; Defense-in-depth gegen
  CSRF.

CSRF-Schutz primär über `SameSite=Strict`; zusätzlich nutzt das
Frontend `X-Requested-With: XMLHttpRequest` (CORS-Origin-Check ist im
Einzel-Origin-Setup nicht relevant).

---

## 4. Sequenz: Registrierung

```
Browser → Hub: POST /api/v1/auth/register
                Body: {email, password, display_name, lang}
Hub:    validate (email RFC, password ≥12 + common-list, lang ∈ {de,en})
        password_hash = argon2id.hash(password, m=64MiB, t=2, p=1)
        users.INSERT
        rt = generate_refresh_token(user_id, family_id=new)
        access = generate_access_token(user_id, role='user', kid=current_kid)
        refresh_tokens.INSERT(user_id, hash(rt), family_id, expires_at, ua, ip_h)
Hub → Browser: 201 Created
        Set-Cookie: access_token, refresh_token
        Body: {user_id, email, display_name}
Hub:    audit_log.INSERT(action='register', actor=user_id, ip_h=...)
```

Validierungs-Fehler:

* Email Regex-Fail → `400 invalid_email`.
* Passwort < 12 oder common → `400 weak_password`.
* Email-Konflikt → `409 email_taken`.
* IP-Rate-Limit → `429 rate_limited` (`Retry-After`-Header).

---

## 5. Sequenz: Login

```
Browser → Hub: POST /api/v1/auth/login
                Body: {email, password}
Hub:    users.SELECT WHERE email=lower(:email) AND is_disabled=0
        if not found: → 401 invalid_credentials (constant-time)
        if not argon2id.verify(password, hash):
            → audit('login_fail_password')
            → quota_usage('login.fail_15m') ++
            if count > 5: ip_blacklist(15m)
            → 401 invalid_credentials
        rt = generate_refresh_token(user_id, family_id=new)
        access = generate_access_token(...)
        refresh_tokens.INSERT
Hub → Browser: 200 OK
        Set-Cookie: access_token, refresh_token
        Body: {user_id, email, display_name, role}
Hub:    audit_log.INSERT(action='login', actor=user_id)
```

* `is_disabled=1` → `403 account_disabled`.
* IP-Blacklist greift → `429 rate_limited`.

---

## 6. Sequenz: Refresh

```
Browser → Hub: POST /api/v1/auth/refresh
                Cookies: refresh_token=<jwt>
Hub:    decode jwt → claims; verify kid in jwks.json
        rt_hash = sha256(jwt-string)
        row = refresh_tokens.SELECT WHERE token_hash=:rt_hash
        if not row or row.revoked or row.expires_at < now:
            → 401 invalid_refresh_token
        if row.rotated_at_ms is not NULL:    # Reuse-Detection
            → see §8 (revoke whole family)
            → 401 refresh_reuse_detected
        # OK: rotate
        new_rt = generate_refresh_token(user_id, family_id=row.family_id)
        new_access = generate_access_token(user_id, ...)
        refresh_tokens.UPDATE row SET rotated_at_ms=now, revoked=0
        refresh_tokens.INSERT(parent_token_id=row.id, family_id=row.family_id, ...)
Hub → Browser: 200 OK
        Set-Cookie: access_token, refresh_token (new values)
        Body: {ok: true}
```

---

## 7. Sequenz: Logout

```
Browser → Hub: POST /api/v1/auth/logout
                Cookies: access_token, refresh_token
Hub:    if refresh_token vorhanden:
            row = refresh_tokens.SELECT WHERE token_hash=...
            UPDATE row SET revoked=1
        Set-Cookie: access_token=; Max-Age=0
        Set-Cookie: refresh_token=; Max-Age=0
Hub → Browser: 200 OK {ok: true}
Hub:    audit_log.INSERT(action='logout')
```

---

## 8. Sequenz: Reuse-Detection

Vorbedingung: ein bereits rotiertes Refresh-Token wird erneut
verwendet (Indikator: Angriff oder Cookie-Klau).

```
Hub:    row = refresh_tokens.SELECT WHERE token_hash=:rt_hash
        if row.rotated_at_ms IS NOT NULL:
            → REVOKE entire family:
              UPDATE refresh_tokens SET revoked=1
              WHERE family_id = row.family_id
            → Set-Cookie clear (access + refresh)
            → audit_log.INSERT(action='refresh_reuse_detected', actor=row.user_id)
            → metrics: terra_auth_token_rotations_total{outcome='reuse_detected'} ++
            → alert A.REFRESH.REUSE (Pager)
            → 401 refresh_reuse_detected
```

Nutzer muss neu einloggen; alle aktiven Sessions sind zerstört.

---

## 9. Sequenz: Engine-Auth (mTLS + JWT)

```
Engine → Cloudflare-Edge:  TLS 1.3 ClientHello + Engine-Cert
CF-Edge: validate cert against ENGINE_CA via mTLS handshake
         forward HTTP-Header CF-Client-Cert to Hub
Engine → Hub (via Edge):  WSS /ws/v1/engine
         Cookies: (none — Engine sends Bearer)
         Headers: Authorization: Bearer <engine-access-jwt>
                  CF-Client-Cert: <pem>
Hub:     parse cert, sha256 → thumbprint
         engine_registrations.SELECT WHERE thumbprint=:t AND is_active=1
         if not found → close 4401 invalid_engine_cert
         decode bearer; verify scope='engine' and sub matches engine.user_id
         if mismatch → close 4403 forbidden
         engine_registrations.UPDATE last_connected_ms=now
         WS welcome
```

Renewal: alle 24 h sendet die Engine `engine/heartbeat`-Frame mit
`bearer_age_s`; bei `> 14d` muss sie erneut über den HTTP-Endpoint
`/api/v1/auth/engine/refresh` (eigener Pfad, nur per mTLS) ein neues
Bearer holen.

---

## 10. Sequenz: Account-Sperre durch Admin

```
Admin-CLI → Hub: POST /api/v1/admin/users/{id}/disable
Hub:    users.UPDATE is_disabled=1, updated_at_ms=now
        refresh_tokens.UPDATE revoked=1 WHERE user_id=:id AND revoked=0
        audit_log.INSERT(actor=admin_id, action='admin.user.disable', target=user_id)
Hub → Admin-CLI: 200 OK
Hub → ws-broadcaster: WS frame to user's viewer channel: {kind: 'forced_logout'}
```

User wird beim nächsten Request mit `403 account_disabled` abgelehnt.

---

## 11. Sequenz: Passwort-Reset (v1.x ergänzt)

> *Hinweis.* In v1.0 nicht implementiert (Email-Versand fehlt). Plan
> für v1.1.x:

```
Browser → Hub:  POST /api/v1/auth/password-reset
                Body: {email}
Hub:    if email exists:
            token = random_url_safe(48)
            password_resets.INSERT(user_id, hash(token), expires_at=now+30min)
            send_email(email, link=`https://terra.example/reset?t={token}`)
        # Stets 202 zurückgeben (kein Email-Enumeration-Leak)
Hub → Browser: 202 Accepted

Browser → Hub:  POST /api/v1/auth/password-reset/confirm
                Body: {token, new_password}
Hub:    row = password_resets.SELECT WHERE token_hash=:h AND consumed=0
                                       AND expires_at > now
        if not row: → 400 invalid_token
        users.UPDATE password_hash = argon2.hash(new_password)
        refresh_tokens.UPDATE revoked=1 WHERE user_id=row.user_id
        password_resets.UPDATE consumed=1
        audit_log.INSERT(action='password.reset.success')
```

---

## 12. Server-State pro Sequenz

* **Login** → `users` Read; `refresh_tokens` INSERT;
  `audit_log` INSERT; `quota_usage` UPSERT bei Fail.
* **Register** → `users` INSERT; alles aus Login.
* **Refresh** → `refresh_tokens` UPDATE (rotated_at) + INSERT (new);
  `audit_log` INSERT.
* **Logout** → `refresh_tokens` UPDATE (revoked); `audit_log` INSERT.
* **Reuse-Detection** → `refresh_tokens` UPDATE (whole family revoked);
  `audit_log` INSERT; Alert.
* **Engine-Auth** → `engine_registrations` Read + UPDATE.
* **Admin-Disable** → `users` UPDATE; `refresh_tokens` UPDATE;
  `audit_log` INSERT; WS-Broadcast.

---

## 13. Test-Pflichten

| Test                                  | Datei                                            |
|---------------------------------------|--------------------------------------------------|
| Register-Validation                   | `tests/auth/test_register_validation.py`         |
| Login-Constant-Time                    | `tests/auth/test_login_timing.py`                |
| Refresh-Rotation                       | `tests/auth/test_refresh_rotation.py`            |
| Refresh-Reuse → Family-Revoke          | `tests/auth/test_refresh_reuse_family.py`        |
| Logout idempotent                       | `tests/auth/test_logout.py`                      |
| Engine-Cert-Validation                  | `tests/auth/test_engine_cert.py`                 |
| Admin-Disable cascade                   | `tests/auth/test_admin_disable.py`               |
| IP-Blacklist nach 5 Fails               | `tests/auth/test_login_ratelimit.py`             |
| Cookie-Flags (`HttpOnly`, `SameSite`)   | `tests/auth/test_cookie_flags.py`                |

Coverage-Ziel: 100 % der Auth-Pfade (incl. Negative-Tests). Skips sind
nicht erlaubt.

---

*Stand: 2026-05-08 · Greenfield-Initial · eingefroren ab v0.5.x ·
referenziert aus `architecture/security.md` §3, `M5-api-surface.md`.*
