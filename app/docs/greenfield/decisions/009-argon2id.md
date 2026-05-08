# ADR-009 — Argon2id für Passwort-Hashing in v1.0

* **Status:** Accepted
* **Datum:** 2026-05-08
* **Bezug:** `architecture/security.md` §3.1,
  `protocols/auth-flow.md`.

## Context

Wir brauchen einen Memory-hard, GPU-resistenten Passwort-Hash.
Klassische Optionen: bcrypt, scrypt, PBKDF2, Argon2id.

Auf der 1-GB-Hub-VM ist Memory knapp; ein zu hoher `m`-Parameter
für Argon2id könnte das Memory-Budget sprengen, wenn mehrere
parallele Login-Versuche zusammenfallen.

## Decision

Wir verwenden **Argon2id** mit Parametern:

* `m = 64 MiB` (memory cost)
* `t = 2` (iterations)
* `p = 1` (parallelism)
* `salt = 16 bytes` (random)
* Encoded-String-Format (`$argon2id$v=19$m=...,t=...,p=...$<salt>$<hash>`).

Rate-Limit pro IP (`POST /auth/login` 10/h, siehe
`architecture/security.md` §7) verhindert, dass mehrere parallele
Logins gleichzeitig den `m`-Cost addieren — ein Worker mit 1 Worker
hält bis zu 4 parallel ausgeführte Argon2id-Hashes (max ≈ 256 MiB
Burst), was Hub-Memory-Reserve abdeckt.

Migration: `passlib`-Library zeigt mit der `verify_and_update`-API
einen Path, falls die Parameter erhöht werden — ein User mit altem
Hash wird beim nächsten erfolgreichen Login automatisch upgedatet.

## Consequences

* **Positiv:**
  * Memory-hard (besser als bcrypt/scrypt für GPU-Angriffe).
  * Einsatz als RFC 9106-konformer Standard.
  * Encoded-String enthält alle Parameter → Migration einfach.
* **Negativ:**
  * 64 MiB `m` ist konservativ; Best-Practice 2025 empfiehlt
    100–256 MiB. v1.x kann nach Benchmark erhöht werden.
* **Neutral:**
  * In v2.0 (M4 mit ≥ 96 GB RAM) wird `m` auf ≥ 128 MiB erhöht
    werden.

## Alternatives Considered

* **bcrypt**: nicht Memory-hard, GPU-Cracking schlechter abgedeckt.
* **scrypt**: gut, aber Argon2id ist neuer und besser unterstützt.
* **PBKDF2-SHA512**: zu schwach gegen modernes GPU-Cracking.

## References

* RFC 9106 (Argon2)
* `passlib`-Doku (Argon2id-Hash-Format)
* `architecture/security.md` §3.1

---

*Greenfield-Initial-ADR.*
