# `M6-frontend-bootstrap.md` — Phase M6: Frontend-Bootstrap

> **Lebendiges Dokument.** Ergebnis: Eine in Produktion auslieferbare
> React-/R3F-Single-Page-App. Login funktioniert, Live-Stream vom Hub
> zeigt Encounters, 3D-Cockpit ist erkennbar, Chat-/Tier-Panels sind
> da, Bundle ist klein genug.
>
> **Phase-Tag bei Abschluss:** `v0.7.0`

---

## Inhalt

1. [Phasen-Ziel](#1-phasen-ziel)
2. [Vorbedingungen](#2-vorbedingungen)
3. [Architektur-Bezug](#3-architektur-bezug)
4. [Schritte M6.1 – M6.13](#4-schritte-m61--m613)
5. [Phasen-Gate](#5-phasen-gate)
6. [Erledigte Änderungen](#6-erledigte-änderungen)

---

## 1. Phasen-Ziel

* Vollständige React-18-App in `frontend/` (Vite + TypeScript +
  React-Router + Zustand + TanStack Query + R3F).
* Auth-Flow mit Hub-Login.
* Live-Stream-Viewer: WS-Verbindung an `/ws/v1/viewer`, Encounters
  erscheinen.
* 3D-Cockpit-Skelett (R3F) zeigt Tier-Hierarchie als Platzhalter-Geometrie.
* Chat-Panel + Tier-Panels (Wells, Concepts, Frameworks).
* Header mit Tier-Counter `T0:N T1:N T2:N T3:N`.
* CSP gehärtet, i18n-Baseline gelegt, Bundle-Size-Gate aktiv.

**Was M6 NICHT tut:**

* Keine Replay-Page-Tiefe (M7).
* Kein voller Diagnostic-View (M7).
* Kein Hardening (M8).

---

## 2. Vorbedingungen

* M5 abgeschlossen (`v0.6.0`).
* OpenAPI v1 frozen, dient als Quelle für Frontend-Types.
* WS-Channel `/ws/v1/viewer` aktiv und stabil.

---

## 3. Architektur-Bezug

* `architecture/mvp.md` §7 — Frontend liest API.
* `architecture/mvp.md` §9 — CSP, XSS, Token-Handling.
* `architecture/mvp.md` §11 — Static-Frontend-Auslieferung über Caddy.
* `Anweisungen.md` §2 — Code-Standards (auch für TS).

---

## 4. Schritte M6.1 – M6.13

---

### M6.1 — frontend-vite-react-ts-baseline

**Branch:** `feature/frontend-vite-react-ts-baseline`
**Issue:** `#NNN`
**Vorbedingungen:** M0 grün
**Berührte Pfade:**
```
frontend/
├── package.json
├── pnpm-lock.yaml                          ← pnpm bevorzugt (kleiner als npm)
├── tsconfig.json                            ← strict
├── vite.config.ts
├── index.html
├── public/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── routes/                              ← React-Router-Routen
│   ├── components/
│   ├── lib/
│   ├── styles/
│   └── types/
├── tests/
│   ├── setup.ts                             ← vitest setup
│   └── App.test.tsx
└── README.md
```

**Akzeptanzkriterien:**
1. Stack:
   * Vite 5+, React 18, TypeScript 5+ (`strict: true`, `noUncheckedIndexedAccess: true`).
   * `react-router-dom` v7+ für Routing.
   * `vitest` + `@testing-library/react` + `playwright` (für Smoke).
   * `eslint` + `@typescript-eslint` + `prettier`.
   * `pnpm` als Package-Manager.
2. `vite.config.ts`:
   * Build-Output `dist/`, gzip+brotli aktiviert.
   * Manifest `manifest.json` für Caddy-Cache-Busting.
3. Basis-Routen:
   * `/` — landing
   * `/login`
   * `/app` — geschützt (Layout)
   * `/app/cockpit`
   * `/app/replay` (Stub für M7)
   * `/app/diagnostic` (Stub für M7)
4. **Type-Generation aus OpenAPI** ist konfiguriert:
   * Tool `openapi-typescript` generiert `src/api/types.ts` aus
     `docs/contracts/openapi/v1.json`. `pnpm generate:api` ist im
     `package.json`.
5. CI:
   * Job `frontend-test` läuft `pnpm test`.
   * Job `frontend-build` baut `dist/` und prüft Existenz.

**Tests:**
* `tests/App.test.tsx::renders_home_link`
* `tests/api/test_types_generated.ts::types_match_openapi_subset`

**Ressourcen-Budget:** Lokales Bundle-Initial < 350 kB gz (in M6.13
verschärft).
**Geschätzte PR-Größe:** ~700 Lines diff
**Fertig wenn:** AC + CI grün; `pnpm dev` läuft.

---

### M6.2 — frontend-auth-flow

**Branch:** `feature/frontend-auth-flow`
**Issue:** `#NNN`
**Vorbedingungen:** M6.1 gemerged
**Berührte Pfade:**
```
frontend/src/auth/
├── LoginPage.tsx
├── AuthProvider.tsx
├── useAuth.ts
├── tokenStorage.ts                          ← memory only
└── refresh.ts                               ← Cookie-basiert
frontend/src/api/client.ts
tests/auth/auth.test.tsx
```

**Akzeptanzkriterien:**
1. Token-Storage: **Access-Token nur im Memory** (Zustand-Store).
   Refresh-Token im HttpOnly-Cookie (Browser, Server-Cookie).
2. `LoginPage`: Email+PW-Form. Validierung clientseitig + serverseitig.
   Bei Erfolg → Navigate zu `/app/cockpit`.
3. `AuthProvider` rehydriert bei App-Start: ruft `/v1/auth/refresh`,
   bekommt neues Access-Token; bei Fehler → `/login`.
4. **Auto-Refresh**: 60 s vor Token-Ablauf wird `/v1/auth/refresh`
   ausgelöst.
5. **Logout-Knopf** im Header: ruft `/v1/auth/logout`, leert Token.
6. Tests: Mocked-Backend, Login → Logout → Refresh-Flow.

**Tests:**
* `tests/auth/auth.test.tsx::login_success`
* `tests/auth/auth.test.tsx::auto_refresh_60s_before_expiry`
* `tests/auth/auth.test.tsx::logout_clears_state`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~600 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M6.3 — frontend-state-mgmt-zustand

**Branch:** `feature/frontend-state-mgmt-zustand`
**Issue:** `—`
**Vorbedingungen:** M6.1 gemerged
**Berührte Pfade:**
```
frontend/src/store/
├── index.ts
├── authStore.ts
├── engineStore.ts                            ← TierCounts, lnn-State
├── encountersStore.ts                        ← Live-Stream-Buffer
└── replayStore.ts                            ← M7
tests/store/
```

**Akzeptanzkriterien:**
1. `zustand` als zentrale Lösung; **kein** Redux, kein MobX.
2. `engineStore.ts` hält:
   * `tierCounts: Record<string, number>`
   * `lnn: { iD, norm, delta, velocity }`
   * `ghostQueue: ...` (Stub)
   * `engineOnline: boolean`
3. `encountersStore.ts` hält Ringpuffer (max 500 Einträge), Aktionen
   `appendEncounter`, `clear`.
4. **Selectors** sind exportierbar; **keine** direkten `useStore()`-
   Aufrufe in komplexen Komponenten ohne Selector.
5. Tests:
   * Mutationen sind Pure-Functions.
   * Subscriptions feuern nur bei tatsächlichen Änderungen (shallow
     compare).

**Tests:**
* `tests/store/engineStore.test.ts::sets_tier_counts`
* `tests/store/encountersStore.test.ts::ring_buffer_eviction`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~400 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M6.4 — frontend-ws-viewer-client

**Branch:** `feature/frontend-ws-viewer-client`
**Issue:** `#NNN`
**Vorbedingungen:** M6.2 gemerged, M6.3 gemerged
**Berührte Pfade:**
```
frontend/src/ws/
├── viewer.ts
├── reconnect.ts
└── frames.ts                                ← Type-Re-Export aus generierten Schemas
tests/ws/viewer.test.ts
```

**Akzeptanzkriterien:**
1. WS-Klasse `ViewerClient`:
   * `connect(url, token)` — öffnet WS mit Subprotocol `terra-viewer.v1`.
   * Empfangene Frames werden gegen TS-Types validiert; bei Schema-
     Verletzung loggen, ignorieren.
   * Dispatch in Stores (engineStore, encountersStore).
2. **Reconnect**: bei Drop exponentielles Backoff, max 30 s, Jitter.
3. **Heartbeat**: alle 10 s `client/pong` schicken (Server liefert
   `server/heartbeat`).
4. **Visibility**: bei `document.hidden` Reconnect verzögern (kein
   Wake-Up-Storm bei Tab-Switch).

**Tests:**
* `tests/ws/viewer.test.ts::connects_and_dispatches_encounter`
* `tests/ws/viewer.test.ts::reconnect_with_backoff`
* `tests/ws/viewer.test.ts::heartbeat_pong_sent`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~500 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M6.5 — frontend-tanstack-query-baseline

**Branch:** `feature/frontend-tanstack-query-baseline`
**Issue:** `—`
**Vorbedingungen:** M6.2 gemerged
**Berührte Pfade:**
```
frontend/src/api/queries/
├── meQuery.ts
├── snapshotsQuery.ts
├── encountersQuery.ts
└── replayQuery.ts                            ← M7-Hauptkonsument
frontend/src/api/mutations/
└── ...
tests/api/queries/
```

**Akzeptanzkriterien:**
1. `@tanstack/react-query` v5+; `QueryClient` mit defaults
   `staleTime: 30s`, `cacheTime: 5min`, retry 1×.
2. Erste Query: `useMe()` ruft `/v1/me`, populiert User in
   AuthStore-Cache.
3. **Coalescing**: Replay-Queries haben Query-Keys, die Filter exakt
   widerspiegeln, damit identische Suchen denselben Cache treffen.
4. **Error-Boundary** in `App.tsx` zeigt globalen Fehler-Banner; Query-
   Fehler propagieren bis dorthin, wenn nicht lokal behandelt.

**Tests:**
* `tests/api/queries/meQuery.test.ts`
* `tests/api/queries/snapshotsQuery.test.ts`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~400 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M6.6 — frontend-r3f-baseline

**Branch:** `feature/frontend-r3f-baseline`
**Issue:** `#NNN`
**Vorbedingungen:** M6.1 gemerged
**Berührte Pfade:**
```
frontend/src/three/
├── Canvas3D.tsx
├── PerformanceMonitor.tsx
├── lights.tsx
├── controls.tsx
└── README.md
tests/three/canvas.test.tsx
```

**Akzeptanzkriterien:**
1. `@react-three/fiber` + `@react-three/drei` aktiv.
2. `Canvas3D` ist die einzige Stelle, die ein `<Canvas>` mountet —
   Wiederverwendung im Cockpit + Replay.
3. **Performance-Monitor** (Drei-Helper) zeigt FPS in Dev-Mode.
4. **Mount/Unmount-Disziplin**: bei Route-Wechsel wird Canvas sauber
   abgebaut (kein WebGL-Leak).
5. Mobile-Fallback: bei `prefers-reduced-motion` oder fehlendem WebGL
   wird Canvas nicht gemountet, sondern Statisch-Banner gezeigt.

**Tests:**
* `tests/three/canvas.test.tsx::mounts_in_dom`
* `tests/three/canvas.test.tsx::unmounts_cleanly_on_route_change`

**Ressourcen-Budget:** R3F-Bundle ~150 kB gz; tritt zur 350 kB-Grenze
in M6.13 hinzu.
**Geschätzte PR-Größe:** ~400 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M6.7 — frontend-r3f-cockpit-skeleton

**Branch:** `feature/frontend-r3f-cockpit-skeleton`
**Issue:** `#NNN`
**Vorbedingungen:** M6.6 gemerged, M6.4 gemerged
**Berührte Pfade:**
```
frontend/src/cockpit/
├── CockpitPage.tsx
├── scene/
│   ├── KGScene.tsx
│   ├── TierLayer.tsx
│   ├── EncounterFlare.tsx
│   ├── LNNHaze.tsx
│   └── camera.tsx
├── overlays/
│   └── ZoomOverlay.tsx
tests/cockpit/
```

**Akzeptanzkriterien:**
1. **`KGScene`** zeigt Knoten als sphärische Glyphen, Tier durch Farb-
   Hierarchie unterscheidbar (Farben aus `Anweisungen.md` §10 +
   `tier_color(N)`-Helfer).
2. **`TierLayer`** rendert pro Tier eine Schicht; Übergang weich
   (`useSpring`).
3. **`EncounterFlare`** triggert kurzes „Aufblitzen" beim
   `encounter_new`-Event (per Subscription auf `encountersStore`).
4. **`LNNHaze`** ist Background-Layer, an `lnn.norm` gekoppelt.
5. **Performance**: stabil 60 fps auf einem mittleren Laptop bei
   bis zu 5 000 Knoten.
6. **Test (Smoke + Snapshot)**:
   * Mount → erste Frame ohne Fehler.
   * Bei Encounter-Event entsteht ein Flare-Mesh (assertable über
     `react-test-renderer` Spy).

**Tests:**
* `tests/cockpit/CockpitPage.test.tsx::mounts_without_error`
* `tests/cockpit/CockpitPage.test.tsx::flare_appears_on_encounter`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~700 Lines diff
**Fertig wenn:** AC + CI grün; UI-Smoke (Playwright) läuft, navigiert
nach `/app/cockpit`, sieht Canvas.

---

### M6.8 — frontend-chat-panel

**Branch:** `feature/frontend-chat-panel`
**Issue:** `#NNN`
**Vorbedingungen:** M6.4 gemerged
**Berührte Pfade:**
```
frontend/src/cockpit/panels/ChatPanel.tsx
frontend/src/cockpit/panels/ChatInput.tsx
tests/cockpit/panels/chat.test.tsx
```

**Akzeptanzkriterien:**
1. Chat-Panel ist **kein** LLM-Wrapper. Es ist:
   * Eingabefeld für ein Wort + optionales Skala-Slider.
   * Submit löst `user/encounter`-Frame über WS aus.
   * History-View zeigt eigene + Engine-erzeugte Encounters.
2. **Auto-Scroll** zum Latest, sofern User nicht hochgescrollt hat.
3. **Eingabe-Validierung**: Wort 1–64 Zeichen, Skala 0.0–10.0 (default
   2.0).
4. Tastatur: Enter sendet, Shift+Enter neue Zeile (vorbereitet, nicht
   verwendet im MVP).

**Tests:**
* `tests/cockpit/panels/chat.test.tsx::submit_emits_user_encounter`
* `tests/cockpit/panels/chat.test.tsx::history_shows_own_message`
* `tests/cockpit/panels/chat.test.tsx::auto_scroll_when_at_bottom`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~450 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M6.9 — frontend-tier-panels

**Branch:** `feature/frontend-tier-panels`
**Issue:** `#NNN`
**Vorbedingungen:** M6.3 gemerged, M6.4 gemerged
**Berührte Pfade:**
```
frontend/src/cockpit/panels/WellsPanel.tsx
frontend/src/cockpit/panels/ConceptsPanel.tsx
frontend/src/cockpit/panels/FrameworksPanel.tsx
frontend/src/cockpit/panels/TierPanelLayout.tsx
tests/cockpit/panels/tier.test.tsx
```

**Akzeptanzkriterien:**
1. Drei Panels (Wells T1, Concepts T2, Frameworks T3) — gemeinsamer
   Layout-Wrapper.
2. Sichtbarkeit per `engineStore.tierCounts` gesteuert: Tier-Panel
   wird erst eingeblendet, sobald `count > 0`.
3. Items werden aus dem `engine/summary`-Stream synchron aktualisiert.
4. **Klick auf Item** triggert eine Server-Aktion `replay/control` (z. B.
   „Fokus auf dieses Konzept") — Stub im MVP, finalisiert in M7.

**Tests:**
* `tests/cockpit/panels/tier.test.tsx::wells_hidden_when_empty`
* `tests/cockpit/panels/tier.test.tsx::wells_shown_when_count_gt_0`
* `tests/cockpit/panels/tier.test.tsx::concepts_render_items`
* `tests/cockpit/panels/tier.test.tsx::click_emits_replay_control`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~500 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M6.10 — frontend-header-counters

**Branch:** `feature/frontend-header-counters`
**Issue:** `—`
**Vorbedingungen:** M6.3 gemerged
**Berührte Pfade:**
```
frontend/src/layout/Header.tsx
frontend/src/layout/TierBadge.tsx
tests/layout/header.test.tsx
```

**Akzeptanzkriterien:**
1. Header zeigt: `T0:N T1:N T2:N T3:N ◌N` (◌ = Ghost-Queue-Length —
   im MVP weiterhin 0).
2. Echtzeit-Update via Selector auf `engineStore`.
3. Engine-Online-Indikator (grüner Punkt) neben User-Avatar.
4. Logout-Button.

**Tests:**
* `tests/layout/header.test.tsx::renders_counts`
* `tests/layout/header.test.tsx::engine_online_indicator`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~250 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M6.11 — frontend-csp-and-security

**Branch:** `feature/frontend-csp-and-security`
**Issue:** `#NNN`
**Vorbedingungen:** M6.1 gemerged
**Berührte Pfade:**
```
frontend/index.html                          ← `<meta http-equiv="Content-Security-Policy" ...>`
deploy/caddy/Caddyfile.frontend              ← CSP-Header serverseitig
docs/operations/frontend-security.md
tests/security/csp.test.ts
```

**Akzeptanzkriterien:**
1. CSP-Policy:
   * `default-src 'self'`
   * `connect-src 'self' wss://<hub>` (über env interpoliert beim
     Build)
   * `img-src 'self' data:`
   * `style-src 'self' 'unsafe-hashes' 'sha256-...'` (für inline-
     style-Reset; kein `'unsafe-inline'` ohne Hash)
   * `script-src 'self'`
   * `worker-src 'self' blob:` (R3F-Loader)
2. **Trusted-Types** (Browser-Best-Practice) aktiv.
3. **`Subresource-Integrity`** für CDN-Assets — wir bevorzugen Self-
   hosted (Caddy serviert alle Assets), daher SRI nur, wo CDN
   unausweichlich (zur Zeit: keine).
4. Doku beschreibt:
   * Wie `connect-src` bei Wechsel des Hub-Hosts angepasst wird.
   * Was bei CSP-Verletzungen im Browser-Console passiert.
   * Reporting-Endpunkt (optional, M8).

**Tests:**
* `tests/security/csp.test.ts::policy_includes_required_directives`
* `tests/security/csp.test.ts::no_unsafe_inline_without_hash`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~250 Lines diff
**Fertig wenn:** AC + CI grün; Smoke im Browser zeigt keine CSP-
Errors.

---

### M6.12 — frontend-i18n-baseline

**Branch:** `feature/frontend-i18n-baseline`
**Issue:** `#NNN`
**Vorbedingungen:** M6.1 gemerged
**Berührte Pfade:**
```
frontend/src/i18n/
├── index.ts
├── en.ts                                     ← Default
└── de.ts                                     ← Stub
frontend/src/components/Translate.tsx
tests/i18n/i18n.test.tsx
```

**Akzeptanzkriterien:**
1. Bibliothek: `react-intl` ODER `i18next` — Entscheidung in PR-Body
   begründet.
2. **EN ist Pflicht-Locale**, weil Backend-KG englisch ist
   (`docs/MULTILINGUAL_AND_SYSTEM_DESIGN.md`).
3. **DE als Stub** für UI-Locale (Backend-KG-Sprache bleibt EN). Strings
   die in DE übersetzt sind, werden gepflegt; nicht übersetzte fallen
   auf EN zurück.
4. **Locale-Switch** ist UI-Sichtbar (Settings-Menu), aber Backend
   erfährt nichts davon — KG-Sprache ist orthogonal.
5. Tests prüfen:
   * Default EN.
   * Switch auf DE übersetzt sichtbare Strings.
   * Fallback auf EN für unbekannte Keys.

**Tests:**
* `tests/i18n/i18n.test.tsx::default_en`
* `tests/i18n/i18n.test.tsx::switch_to_de`
* `tests/i18n/i18n.test.tsx::fallback_to_en_on_missing`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~350 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M6.13 — frontend-bundle-size-gate

**Branch:** `chore/frontend-bundle-size-gate`
**Issue:** `—`
**Vorbedingungen:** M6.1 – M6.12 gemerged
**Berührte Pfade:**
```
frontend/scripts/bundle-size-check.ts
.github/workflows/ci.yml                    ← Job `frontend-bundle`
docs/operations/frontend-bundle.md
```

**Akzeptanzkriterien:**
1. CI-Job baut `dist/`, misst initial-JS-Bundle (gz).
2. Limit: **350 kB gz initial**, plus 200 kB gz für die Cockpit-Route
   (lazy).
3. Bei Überschreitung: CI-Fail mit klarem Fehlertext, der den
   Code-Splitter bittet, neue dynamic-imports einzuführen.
4. Doku zeigt, wie man im Bundle nachsieht (`pnpm run analyze`).

**Tests:**
* CI-Job-Existenz wird durch erfolgreiche Pipeline bewiesen.

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~200 Lines diff
**Fertig wenn:** Erste PR nach Merge respektiert das Limit.

---

## 5. Phasen-Gate

M6 gilt als grün, wenn:

1. M6.1 – M6.13 in `00-index.md` auf `[x]`.
2. Manueller Smoke: User loggt sich auf der Live-VM ein, sieht
   Cockpit, Encounter erscheinen, Tier-Badges aktualisieren sich.
3. Bundle-Size-Gate ist Pflicht-Check.
4. Tag `v0.7.0` gepusht.

---

## 6. Erledigte Änderungen

— *(noch leer)*

---

*Stand: 2026-05-08 · Greenfield-Initial · M6 noch nicht eröffnet*
