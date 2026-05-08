# `architecture/frontend.md` — Frontend-Architektur (v1.0)

> **Zweck.** Vollständige Architektur des React-/three.js-Frontends
> für v1.0. Ergänzt `implementation/mvp/M6-frontend-bootstrap.md`
> (was wann wo) und `protocols/replay-contract.md` (was bekommt das
> Frontend zurück). Bindet sich an `architecture/mvp.md`
> (Hosting, Cloudflare-Tunnel) und `architecture/security.md` §6
> (Output-Encoding, CSP).

---

## Inhalt

1. [Stack & Build-Pipeline](#1-stack--build-pipeline)
2. [Routing & Pages](#2-routing--pages)
3. [Komponenten-Hierarchie](#3-komponenten-hierarchie)
4. [State-Management](#4-state-management)
5. [Datenfluss & API-Client](#5-datenfluss--api-client)
6. [WebSocket-Lebenszyklus](#6-websocket-lebenszyklus)
7. [3D-Cockpit (R3F)](#7-3d-cockpit-r3f)
8. [i18n](#8-i18n)
9. [Theming & Tokens](#9-theming--tokens)
10. [Performance-Vertrag (Web Vitals)](#10-performance-vertrag-web-vitals)
11. [Accessibility](#11-accessibility)
12. [Tests](#12-tests)
13. [Deployment](#13-deployment)

---

## 1. Stack & Build-Pipeline

* **React 18.3** mit Hooks-only-Stil (keine Class-Components).
* **Vite 5.x** als Bundler; Modul-Splitting per Route.
* **TypeScript 5.4** mit `strict: true`, `noImplicitAny`,
  `noUncheckedIndexedAccess`.
* **State:** **Zustand 4.x** (lightweight, kein Boilerplate).
* **Server-State:** **TanStack Query 5.x** (HTTP-Cache, Stale-while-
  Revalidate).
* **3D:** **`@react-three/fiber` 8.x** + **`@react-three/drei` 9.x**;
  three.js 0.165+.
* **Tests:** **Vitest 1.x**, **React Testing Library**, **Playwright** für
  E2E-Smoke.
* **Linting:** ESLint 9.x mit `eslint-plugin-react`,
  `@typescript-eslint`, `prettier-plugin`.
* **Bundle-Gates:** Bundle-Size-Cap für `index.js` ≤ 250 KB gzip,
  `cockpit-3d-chunk.js` ≤ 400 KB gzip (siehe `M6.13`).
* **OpenAPI-Codegen:** `pnpm gen:api` erzeugt typed-Client aus
  `docs/contracts/openapi/v1.json`.

---

## 2. Routing & Pages

* **Router:** `react-router-dom` 6.x.
* **Routen** (alle public-prefix `/`):

| Pfad             | Page-Komponente            | Zugriff                  |
|------------------|----------------------------|--------------------------|
| `/`              | `<LandingPage>`            | öffentlich                |
| `/login`         | `<LoginPage>`              | öffentlich                |
| `/register`      | `<RegisterPage>`           | öffentlich                |
| `/cockpit`       | `<CockpitPage>`            | auth                     |
| `/replay`        | `<ReplayPage>`             | auth                     |
| `/diagnostic`    | `<DiagnosticPage>`         | auth                     |
| `/settings`      | `<SettingsPage>`           | auth                     |
| `/admin`         | `<AdminConsole>`            | auth + `role=admin`       |
| `*`              | `<NotFound>`                | öffentlich                |

* **Auth-Guard:** `<RequireAuth role?>` wrappt alle privaten
  Routen.
* **Lazy-Load:** `/cockpit`, `/replay`, `/admin` sind als dynamische
  Imports ausgewiesen — Bundle-Initial bleibt klein.

---

## 3. Komponenten-Hierarchie

```
<App>
 ├── <RouterProvider>
 │    ├── <PublicLayout>          (Landing/Login/Register)
 │    └── <AppLayout>              (alle privaten Pages)
 │         ├── <Topbar>             (Brand, User-Menu, Lang-Switch, Status-Dot)
 │         ├── <Sidebar>            (Cockpit / Replay / Diagnostic / Settings)
 │         ├── <PageOutlet/>
 │         └── <ToastsRoot/>
 └── <Providers>
      ├── <QueryClientProvider>     (TanStack Query)
      ├── <I18nProvider>            (i18next)
      ├── <ThemeProvider>           (CSS Variablen)
      └── <WSProvider>              (WS-Client für Viewer)
```

**Page-spezifische Bäume:**

* `<CockpitPage>` → `<R3FCanvas>` (`<CockpitScene>` → `<UniverseGroup>`,
  `<TierLayers>`, `<EngineStatusOverlay>`, `<ZoomControls>`,
  `<Lighting>`).
* `<ReplayPage>` → `<ReplayHeader>`, `<ReplayQueryBar>`, `<ReplayList>`,
  `<DensityMini>`, `<EngineControl>` (Pause/Step/Speed).
* `<DiagnosticPage>` → `<HealthSummary>`, `<MetricChart>`,
  `<EnginePanel>`, `<NATSPanel>`, `<LitestreamPanel>`.

---

## 4. State-Management

* **Drei Stores** (Zustand) — **klare Trennung:**
  * `authStore` — `user`, `role`, `lang`, `isLoading`,
    `isAuthenticated`, `loginAction`, `logoutAction`,
    `refreshAction`. Persistiert nichts (`HttpOnly`-Cookies sind
    Server-State).
  * `viewerStore` — Live-Stream aus WS:
    `events: EventBuffer`, `engineStatus: 'online'|'offline'|'lag'`,
    `tierMaxSeen: number`, `wells: WellSummary[]`, …
  * `uiStore` — UI-State, der nicht aus Daten kommt:
    `sidebarOpen`, `themeName`, `langOverride`,
    `replayQueryDraft`, `cockpitCameraPreset`.

* **Server-State** (HTTP) gehört in TanStack Query, **nicht** in
  Zustand. Beispiele: `useReplayWindow(filter)`,
  `useSnapshots()`, `useDiagnostic()`.

* **Selektoren** (Zustand) sind sliced — keine Komponente abonniert
  unnötig den ganzen Store.

---

## 5. Datenfluss & API-Client

* **API-Client** (`src/api/client.ts`):
  * Basis-URL `/api/v1`.
  * `credentials: 'include'` für Cookies.
  * 401-Handler: ruft `refresh` auf; bei 401-`refresh_reuse_detected`
    → globaler Logout + Toast.
  * Type-Codegen aus OpenAPI; jede Funktion typed.
* **TanStack Query Defaults**:
  * `staleTime: 30s`,
  * `retry: 2 (jitter)`,
  * `refetchOnWindowFocus: false` für `replay/window`-Queries.
* **Mutationen** (`POST/PATCH/DELETE`) → invalidieren passende
  `queryKey`s.

---

## 6. WebSocket-Lebenszyklus

* `<WSProvider>` öffnet **eine** Verbindung zu
  `wss://terra.example/ws/v1/viewer` nach Auth.
* **Reconnect-Strategie**: exponential Backoff
  `[1s, 2s, 5s, 10s, 30s, 60s]`, danach 60 s konstant.
* **Heartbeat**: Client sendet `ping` alle 30 s; Server antwortet
  `pong { ts_ms }`. Latenz wird in `viewerStore.engineLatencyMs`
  protokolliert.
* **Backpressure**: bei > 5 s ohne Pong → UI zeigt Warning, ab 10 s
  reconnect.
* **Pause/Resume**: bei `document.hidden = true` schließt Client
  Verbindung nach 5 min Inaktivität (Mobile-Battery-Saving).

---

## 7. 3D-Cockpit (R3F)

### 7.1 Szenen-Aufbau

* **Wurzel:** `<UniverseGroup>` als Anker; alle Tier-Layer kreisen
  in z=0.
* **Tier-Layer:** Eine `<TierLayer tier={n}>`-Gruppe pro Tier; Knoten
  als **Instanced-Mesh** (ein Draw-Call) mit Color-Attribute pro
  Tier-Farb-Token (siehe §9).
* **Wells:** `<WellHalo>` als zusätzlicher Ring um Wells; Mesh aus
  RingBufferGeometry, Instanced.
* **Edges:** Linien-Buffer (3 Vertices pro Edge), maximal 4096 Edges
  visualisiert (Subsampling über `seen_count`).
* **Lighting:** `<ambientLight intensity={0.4}>` +
  `<directionalLight position={[5,5,5]} intensity={0.6}>` +
  optional `<pointLight>` an aktivem Tier.

### 7.2 Performance-Maßnahmen

* `useFrame` ohne State-Updates (keine setState im Render-Loop).
* `<Instances>` aus `@react-three/drei` pro Knoten-/Edge-Klasse.
* `useMemo` für Geometrien.
* `dispose: true` beim Unmount (Memory-Leak-Vermeidung).
* `<Stats>`-Overlay nur in Dev-Build.

### 7.3 Interaktion

* `<OrbitControls>` mit `enableDamping=true`, `enablePan=false`.
* Picking via `useRaycaster`; Klick auf Knoten → `uiStore.setSelectedNode`.
* Doppel-Klick → Zoom-to-Node (Camera-Animation per `useSpring`).

---

## 8. i18n

* **Bibliothek:** `i18next` 23.x + `react-i18next`.
* **Sprachen v1.0:** `de`, `en`. v1.1 ergänzt `fr`, `it`.
* **Bundles** in `src/locales/<lang>/<ns>.json`. Namespaces:
  `common`, `auth`, `cockpit`, `replay`, `diagnostic`, `errors`.
* **Pluralisierung** über ICU MessageFormat.
* **Fallback-Logik:** `users.preferred_lang` → URL-Override
  (`?lang=en`) → Browser-`navigator.language` → `de`.
* **Build-Gate:** Tests prüfen, dass kein Schlüssel fehlt; CI-Check
  `pnpm i18n:lint`.

---

## 9. Theming & Tokens

* **CSS-Variablen** statt eines CSS-in-JS-Frameworks.
* **Token-Schichten** (`src/styles/tokens/*`):
  * `color.tokens.css` — Primärpalette (Brand, Accent, Background,
    Surface, Text).
  * `tier.tokens.css` — Farben pro Tier (`--tier-0` … `--tier-5`).
  * `space.tokens.css`, `font.tokens.css`, `motion.tokens.css`.
* **Themes:** `light`, `dark`, `auto` (folgt System).
* **Reduced-Motion**: respektiert
  `@media (prefers-reduced-motion: reduce)` — Animationen werden
  geslowed bzw. durch Snapshots ersetzt.

---

## 10. Performance-Vertrag (Web Vitals)

| Metric                    | Mobile-Ziel | Desktop-Ziel | Quelle               |
|---------------------------|-------------|--------------|-----------------------|
| LCP (Largest Contentful Paint) | < 2.5 s    | < 1.5 s     | `terra_frontend_lcp_seconds` |
| INP (Interaction to Next Paint) | < 200 ms  | < 100 ms    | `terra_frontend_inp_ms` |
| CLS (Cumulative Layout Shift)  | < 0.1     | < 0.05      | `terra_frontend_cls`  |
| Bundle Initial             | ≤ 250 KB gzip | ≤ 250 KB gzip | M6.13 gate         |
| Cockpit-3D-Chunk            | ≤ 400 KB gzip | ≤ 400 KB gzip | M6.13 gate         |
| Time-to-Interactive (3G)    | < 4 s       | n/a         | Lighthouse-CI         |

---

## 11. Accessibility

* **WCAG 2.1 AA** als Ziel.
* **Keyboard-Navigation** vollständig: alle interaktiven Elemente
  erreichbar via Tab/Shift-Tab.
* **Focus-Indikatoren** sichtbar (CSS `:focus-visible`).
* **ARIA-Roles** korrekt für Listen, Buttons, Dialoge.
* **Color-Contrast** ≥ 4.5:1 für Text gegen Background.
* **Screen-Reader-Test** mit NVDA + VoiceOver pro Release.
* **3D-Fallback** unter `<noscript>`-Block für Replay-Page (statische
  Tabelle der jüngsten Events).

---

## 12. Tests

| Ebene         | Werkzeug | Was                                 |
|---------------|----------|--------------------------------------|
| Unit          | Vitest   | Hooks, Utilities, Reducer            |
| Component     | Vitest + RTL | UI-Komponenten in Isolation       |
| Integration   | Vitest + MSW | TanStack-Query-Flows, WS-Mocks     |
| E2E (Smoke)   | Playwright | Happy-Path Login → Replay → Logout |
| Visual        | Playwright + Chromatic | Snapshot-Diff für Cockpit-Page |
| Accessibility | axe-playwright | WCAG-Checks pro Release           |
| Bundle        | `size-limit`-CLI | Bundle-Caps                       |
| i18n          | `pnpm i18n:lint`  | fehlende Keys                     |

Coverage-Ziel: 80 % unit + component, 100 % auf Auth-Hooks.

---

## 13. Deployment

* **Hosting:** Cloudflare Pages (kostenlos).
  * Build-Trigger: GitHub-Push auf `main`.
  * Vorschau-Deploys pro PR (Cloudflare Pages Preview).
* **DNS:**
  * `terra.example` → Cloudflare Pages.
  * `/api/*` und `/ws/*` werden über CF-Worker zur Hub-VM weiter­
    geleitet.
* **Asset-Caching:**
  * `index.html` `Cache-Control: no-cache, max-age=0`.
  * Hash-suffixed JS/CSS/Asset-Dateien `Cache-Control: public,
    max-age=31536000, immutable`.
* **CSP** (per Caddy-Header):
  ```
  Content-Security-Policy:
    default-src 'self';
    script-src 'self';
    style-src 'self' 'unsafe-inline';
    img-src 'self' data:;
    font-src 'self';
    connect-src 'self' wss://terra.example;
    frame-ancestors 'none';
    object-src 'none';
    base-uri 'self';
    form-action 'self';
  ```
* **Deployment-Smoke-Test (Playwright)**: 5 Schritte (Landing →
  Register Test-User → Login → Cockpit → Logout). Bei Fehler:
  Auto-Rollback auf vorherigen Cloudflare-Pages-Build.

---

*Stand: 2026-05-08 · Greenfield-Initial · referenziert aus
`implementation/mvp/M6-frontend-bootstrap.md`,
`protocols/replay-contract.md`, `architecture/security.md`.*
