# `M3-local-engine-skeleton.md` — Phase M3: Lokale Engine — Skelett

> **Lebendiges Dokument.** Ergebnis: Eine installierbare Local Engine
> (Python-Paket `terra-engine`), die sich am Hub anmeldet, einen
> Stub-Tick-Loop laufen lässt, Encounter-Events emittiert, periodisch
> Summaries schickt und Snapshots schreibt — alles **ohne** echte
> LNN/EBM/KG-Berechnung. Die echte Mathematik beginnt in M4.
>
> **Phase-Tag bei Abschluss:** `v0.4.0`

---

## Inhalt

1. [Phasen-Ziel](#1-phasen-ziel)
2. [Vorbedingungen](#2-vorbedingungen)
3. [Architektur-Bezug](#3-architektur-bezug)
4. [Schritte M3.1 – M3.9](#4-schritte-m31--m39)
5. [Phasen-Gate](#5-phasen-gate)
6. [Erledigte Änderungen](#6-erledigte-änderungen)

---

## 1. Phasen-Ziel

* **`engine/`** ist ein eigenes Sub-Paket mit `pyproject.toml`,
  installierbar via `uv pip install -e ./engine`.
* **CLI** `terra-engine`:
  * `connect <hub>` — verbindet sich, läuft im Vordergrund
  * `status` — Engine-Selbstdiagnose
  * `snapshot --scope full|delta` — explizite Snapshot-Erzeugung
  * `replay-load <file>` — späterer Hook, M7
* **Stub-Tick-Loop** läuft 8 Hz, generiert deterministisch
  pseudo-zufällige Encounter (für Demos), schickt Summaries.
* **Konformität** mit dem M2-Engine-Protokoll: jede Frame-Form valide.

**Was M3 NICHT tut:**

* Keine echte LNN/EBM/KG-Mathematik. Stubs liefern Plausibilitäts-Werte.
  Echte Mathematik kommt mit `F.LNN.STATE.001` in M4.
* Keine Persistenz von KG-Knoten — Engine hält Zustand nur in-memory
  und in einer kleinen lokalen SQLite (für Wiederanlauf-Resilienz).

---

## 2. Vorbedingungen

* M2 abgeschlossen, `v0.3.0` getaggt.
* Test-Engine aus `tests/integration/test_engine_roundtrip.py` lieferte
  einen funktionierenden Smoke. Wir packen denselben Code in das
  installierbare Paket.

---

## 3. Architektur-Bezug

* `architecture/mvp.md` §4 — Service-Inventar, Local Engine
* `architecture/mvp.md` §8 — Engine-Protokoll
* `Anweisungen.md` §7 — Non-Negotiables: `lnn_step()`,
  `find_energy_wells()`, immutable Member-Sets — werden im Stub als
  **Schnittstellen-Stubs** angelegt, damit M4 nahtlos einsteigen kann.
* `docs/ARCHITECTURE.md` §1–§5 — Mathematik-Referenz für die spätere
  Befüllung.

---

## 4. Schritte M3.1 – M3.9

---

### M3.1 — engine-package-skeleton

**Branch:** `feature/engine-package-skeleton`
**Issue:** `#NNN`
**Vorbedingungen:** M2 grün
**Berührte Pfade:**
```
engine/
├── pyproject.toml
├── README.md
├── src/terra_engine/
│   ├── __init__.py
│   ├── version.py
│   ├── config.py
│   ├── locale.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── state.py                       ← `EngineState` dataclass
│   │   ├── lnn.py                          ← Stub-Klasse
│   │   ├── ebm.py                          ← Stub-Klasse
│   │   └── kg.py                           ← Stub-Klasse
│   ├── runtime/
│   │   ├── __init__.py
│   │   ├── tick_loop.py                   ← Stub
│   │   ├── encounter_source.py             ← deterministische Pseudo-Encounter
│   │   └── snapshot.py                     ← Bundle-Schreiber
│   ├── transport/
│   │   ├── __init__.py
│   │   ├── ws_client.py                    ← async WS-Client zum Hub
│   │   └── frames.py                       ← (re-)imported aus backend?
│   └── cli/
│       └── __main__.py                     ← `python -m terra_engine`
└── tests/
    ├── test_state.py
    ├── test_config.py
    └── test_locale.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. `engine/pyproject.toml` deklariert:
   * `requires-python = ">=3.12"` (M4-Hardware kann später auf 3.13t)
   * Dependencies (Stub-Stand): `numpy`, `aiohttp` (oder `websockets`),
     `pydantic`, `aiosqlite`, `typer` (CLI), `structlog` (Logging),
     `prometheus_client` (Metriken)
   * **Bewusst KEIN `torch`** in M3. Torch kommt erst, wenn M4
     `F.LNN.STATE.*` implementiert.
2. **`engine/src/terra_engine/transport/frames.py`** importiert die
   WS-Schemas aus M2.1 ohne Code-Duplikation. Strategie:
   * Schemas leben in `docs/contracts/ws/`. Beim Build laufen
     Codegen-Schritte, die die Pydantic-Modelle in beiden Paketen
     (`backend.api.ws.schemas` und `terra_engine.transport.frames`)
     aktualisieren.
   * Alternative: gemeinsames Sub-Paket `terra_contracts`, das beide
     Importieren — bevorzugt.
3. `terra-engine`-Konsolen-Skript ist installiert (`[project.scripts]`).
4. Der Befehl `terra-engine --help` listet alle Subkommandos.

**Tests:**
* `tests/test_state.py::test_engine_state_default_values`
* `tests/test_config.py::test_config_loads_from_env`
* `tests/test_locale.py::test_locale_default_en`

**Ressourcen-Budget:** Pakete werden auf der Workstation installiert,
nicht auf VMs. M3 verbraucht **null** Hub-RAM.
**Geschätzte PR-Größe:** ~700 Lines diff
**Fertig wenn:** AC + CI grün; `pip install -e ./engine` funktioniert.

---

### M3.2 — engine-cli

**Branch:** `feature/engine-cli`
**Issue:** `#NNN`
**Vorbedingungen:** M3.1 gemerged
**Berührte Pfade:**
```
engine/src/terra_engine/cli/
├── __init__.py
├── connect.py
├── status.py
├── snapshot.py
└── replay_load.py                          ← noop in M3, signalisiert „nicht aktiv"
engine/tests/cli/test_cli.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. CLI ist `typer`-basiert.
2. Subkommandos:
   * `terra-engine connect <hub-url> [--cert PATH] [--token PATH]`
     — startet die Engine im Vordergrund, läuft bis SIGINT.
   * `terra-engine status` — gibt Snapshot der `EngineState` als JSON
     aus.
   * `terra-engine snapshot --scope full|delta --out PATH` — schreibt
     ein Bundle, ohne den Hub zu kontaktieren (offline-fähig).
   * `terra-engine replay-load <file>` — gibt freundlich `not yet
     supported in v0.4` aus.
3. Logging: `--log-level info|debug|warning`, Default `info`. JSON-Lines
   auf STDERR, Daten auf STDOUT.
4. Exit-Codes: 0 bei sauberem Shutdown, 130 bei SIGINT, > 0 bei
   Fehlern.
5. Tests: jede Subroutine wird im CLI-Runner-Mode aufgerufen.

**Tests:**
* `tests/cli/test_cli.py::test_status_outputs_json`
* `tests/cli/test_cli.py::test_snapshot_writes_file`
* `tests/cli/test_cli.py::test_help_prints_subcommands`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~400 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M3.3 — engine-config-and-locale

**Branch:** `feature/engine-config-and-locale`
**Issue:** `#NNN`
**Vorbedingungen:** M3.1 gemerged
**Berührte Pfade:**
```
engine/src/terra_engine/config.py
engine/src/terra_engine/locale.py
engine/tests/test_config_full.py
engine/tests/test_locale_full.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. `config.py` enthält **alle** numerischen Start-Parameter (Bestand
   aus `Anweisungen.md` §10 + neue für die Engine):
   * `lnn_B = 256`
   * `tick_hz = 8`
   * `kg_node_limit = 16_000`
   * `ebm_theta = 0.18`
   * `ebm_tick_cadence = 4`
   * `well_grace_s = 5_400`
   * Engine-spezifisch:
     * `connect_timeout_s = 10`
     * `reconnect_backoff_base_s = 2`
     * `reconnect_backoff_max_s = 60`
     * `summary_interval_s = 1`
     * `snapshot_interval_full_s = 600`
     * `snapshot_interval_delta_s = 60`
2. `locale.py` enthält **alle** Labels (Bestand aus `Anweisungen.md` §10
   plus Engine-spezifische Status-Labels). Locale wird **vor Boot**
   gesetzt; Wechsel zur Laufzeit ist nicht erlaubt (vgl.
   `Anweisungen.md` §7 *Config / Locale*).
3. ENV-Override: `TERRA_LNN_B`, `TERRA_TICK_HZ`, … Pattern wie
   `TERRA_<UPPER_KEY>`.
4. Tests:
   * Default-Werte stabil.
   * ENV-Override funktioniert.
   * Locale-Wechsel zur Laufzeit wirft `LocaleLockedError`.

**Tests:**
* `tests/test_config_full.py::test_defaults_match_anweisungen`
* `tests/test_config_full.py::test_env_override`
* `tests/test_locale_full.py::test_locale_wechsel_zur_laufzeit_blockiert`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~250 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M3.4 — engine-state-bootstrap

**Branch:** `feature/engine-state-bootstrap`
**Issue:** `#NNN`
**Vorbedingungen:** M3.3 gemerged
**Berührte Pfade:**
```
engine/src/terra_engine/core/state.py
engine/src/terra_engine/core/registry.py    ← Tier-Registry-Stub
engine/src/terra_engine/persistence/local_db.py
engine/tests/core/test_state.py
engine/tests/persistence/test_local_db.py
```

**Formel-Refs:** Stubs für `F.LNN.STATE.*`, `F.EBM.WELL.*`, `F.KG.*` (real in M4)

**Akzeptanzkriterien:**
1. `EngineState` ist eine `@dataclass`:
   * `lnn: LNNStub`
   * `ebm: EBMStub`
   * `kg: KGStub`
   * `tier_registry: TierRegistry` — leeres `dict[int, list[str]]`
   * `tick: int = 0`
   * `started_at: float`
2. `lnn_step()` ist als **stub** definiert, lehrt sich aus
   `Anweisungen.md` §7:
   * Pflicht-Signatur `lnn_step(word, scale, state)`.
   * Stub-Body: erhöht `state.tick`, dispatched an `LNNStub.step` mit
     deterministisch konstruiertem Vektor (kein echtes CfC-Update).
3. `find_energy_wells()` ist als Stub definiert: gibt aktuell registrierte
   Wells aus `state.ebm.wells` zurück, sortiert nach Tier.
4. **Local SQLite** für Engine-Resilience:
   * Pfad konfigurierbar (`engine_db_path`, default `~/.terra-engine/engine.sqlite`).
   * Tabellen: `tick_log`, `pending_encounters`, `snapshots_local`.
   * Wenn Engine connectet, sendet sie pending_encounters; bei Erfolg
     löscht sie sie.

**Tests:**
* `tests/core/test_state.py::test_state_initializes_clean`
* `tests/core/test_state.py::test_lnn_step_is_singleton_entrypoint`
* `tests/persistence/test_local_db.py::test_pending_encounters_round_trip`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~500 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M3.5 — engine-tick-loop-stub

**Branch:** `feature/engine-tick-loop-stub`
**Issue:** `#NNN`
**Vorbedingungen:** M3.4 gemerged
**Berührte Pfade:**
```
engine/src/terra_engine/runtime/tick_loop.py
engine/src/terra_engine/runtime/scheduler.py
engine/tests/runtime/test_tick_loop.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. Tick-Loop ist `async def run_tick_loop(state, transport)`:
   * Loop mit `asyncio.sleep(1 / config.tick_hz - elapsed)`.
   * Bei Drift > 1 Tick → Log-Warning + Skip-Counter.
2. **Pause/Play/Speed**-Steuerung via `replay_command`-Frames vom Hub
   wird respektiert:
   * `pause` → Loop sleept, kein Tick wird verarbeitet.
   * `play` → resume.
   * `speed` → Multiplikator auf `tick_hz`.
3. Tick-Body in M3 ist Stub: nur State-`tick`-Counter erhöhen,
   gelegentlich `encounter_source` befragen.
4. **Determinismus für Tests**: bei festgelegtem Seed produziert das
   Stub identische Encounter-Sequenzen.

**Tests:**
* `tests/runtime/test_tick_loop.py::test_8hz_loop`
* `tests/runtime/test_tick_loop.py::test_pause_resume`
* `tests/runtime/test_tick_loop.py::test_speed_multiplier`
* `tests/runtime/test_tick_loop.py::test_deterministic_with_seed`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~450 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M3.6 — engine-encounter-emitter

**Branch:** `feature/engine-encounter-emitter`
**Issue:** `#NNN`
**Vorbedingungen:** M3.5 gemerged
**Berührte Pfade:**
```
engine/src/terra_engine/runtime/encounter_source.py
engine/src/terra_engine/runtime/encounter_emitter.py
engine/tests/runtime/test_encounter_emitter.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. `EncounterSource`:
   * Mode `demo` — deterministisch aus einer Wortliste in
     `engine/data/demo_words.txt` (klein, dokumentiert).
   * Mode `stdin` — liest Encounter-Anfragen von stdin (für CLI-Tests).
   * Mode `replay-file` — lädt eine `.jsonl`-Datei mit Encounters.
2. `EncounterEmitter` ruft `transport.send_engine_encounter(...)` auf,
   prüft Schema, persistiert lokal in `pending_encounters`, löscht bei
   Hub-Ack.
3. Bei Verbindungsverlust: Encounter sammeln sich in
   `pending_encounters` an; nach Reconnect werden sie in der
   ursprünglichen Reihenfolge gesendet.
4. **Rate-Self-Limit**: Engine generiert nicht mehr als
   `config.tick_hz × max_encounter_per_tick` Encounters; Default
   `max_encounter_per_tick = 1` (8/s).

**Tests:**
* `tests/runtime/test_encounter_emitter.py::test_emit_round_trip`
* `tests/runtime/test_encounter_emitter.py::test_offline_buffering`
* `tests/runtime/test_encounter_emitter.py::test_rate_limit`
* `tests/runtime/test_encounter_emitter.py::test_demo_seed_deterministic`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~400 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M3.7 — engine-summary-emitter

**Branch:** `feature/engine-summary-emitter`
**Issue:** `#NNN`
**Vorbedingungen:** M3.5 gemerged
**Berührte Pfade:**
```
engine/src/terra_engine/runtime/summary_emitter.py
engine/tests/runtime/test_summary_emitter.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. `SummaryEmitter` läuft alle `summary_interval_s` (Default 1 s):
   * Sammelt `tier_counts`, `lnn`, `ghost_queue` aus dem State.
   * Schickt `engine/summary` an den Hub.
2. **In M3 sind die Werte Stubs**:
   * `tier_counts`: `{T0: 0, T1: 0, T2: 0, T3: 0}` (wächst, sobald M4
     EBM-Wells ausspuckt).
   * `lnn`: `{iD: lnn_B, norm: 0.0, delta: 0.0}` als Default.
   * `ghost_queue`: leer.
3. Sobald M4 echte Werte produziert, ändert sich nur die State-
   Bestückung — nicht der Emitter.

**Tests:**
* `tests/runtime/test_summary_emitter.py::test_summary_at_interval`
* `tests/runtime/test_summary_emitter.py::test_schema_valid`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~250 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M3.8 — engine-snapshot-write-stub

**Branch:** `feature/engine-snapshot-write-stub`
**Issue:** `#NNN`
**Vorbedingungen:** M3.4 gemerged
**Berührte Pfade:**
```
engine/src/terra_engine/runtime/snapshot.py
engine/src/terra_engine/runtime/bundle.py
engine/tests/runtime/test_snapshot.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. Snapshot-Bundle-Format (eingefroren ab M3 — siehe
   `architecture/mvp.md` §1 *Eingefroren*):
   ```
   <bundle>.tar.zst
   ├── manifest.json     ← schema_v, ts, scope, engine_version, contents-list
   ├── lnn.bin           ← LNN-Gewichte (NumPy-mmap, in M3 leer)
   ├── ebm.bin            ← EBM-Wells (in M3 leer)
   ├── kg.json.zst         ← KG-Knoten/Kanten (in M3 leer)
   └── tick_log.jsonl.zst   ← jüngste Tick-Schnipsel (M3 zur Plausibilisierung)
   ```
2. `manifest.json` ist gegen ein Schema validiert (`docs/contracts/snapshots/manifest.v1.schema.json`).
3. `bundle.py`:
   * `write_full_bundle(state, path)`
   * `write_delta_bundle(state, base_snapshot_id, path)` — in M3 wirft
     dieser eine `NotImplementedError("delta requires M4")`, weil ohne
     echtes LNN-Gewicht-Diff sinnlos.
4. Snapshot-Upload-Pfad (über M2.6) wird verifiziert:
   Hub akzeptiert das von der Engine erzeugte Bundle.

**Tests:**
* `tests/runtime/test_snapshot.py::test_write_full_bundle_validates`
* `tests/runtime/test_snapshot.py::test_delta_not_implemented_in_m3`
* `tests/integration/test_snapshot_upload_to_hub.py::test_engine_uploads_full_bundle`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~500 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M3.9 — engine-protocol-conformance-tests

**Branch:** `test/engine-protocol-conformance-tests`
**Issue:** `—`
**Vorbedingungen:** M3.6, M3.7, M3.8 gemerged
**Berührte Pfade:**
```
engine/tests/conformance/
├── __init__.py
├── conftest.py                            ← Hub-Fixtures
├── test_handshake.py
├── test_encounter_flow.py
├── test_summary_flow.py
├── test_snapshot_flow.py
├── test_disconnect_flow.py
└── test_singleton_engine.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. **Vollständigkeit**: Jeder Frame-Typ aus M2.1 hat mindestens einen
   Test, der einen Engine-Hub-Roundtrip prüft.
2. Tests laufen sowohl gegen In-Process Hub (TestClient) als auch gegen
   den echten Compose-Stack (`pytest-docker-compose`-Marker).
3. **Negative Suite**: bewusst falsche Frames (Schema-Verletzung,
   falsche `schema_v`, fehlender Subprotocol-Header) → Engine wird
   geschlossen, Counter erhöht.
4. **Stress-Test (smoke)**: Engine läuft 10 min, 8 Hz, ohne Memory-Leak,
   ohne Connection-Drop.

**Tests:** wie oben gelistet.

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~700 Lines diff
**Fertig wenn:** AC + CI grün.

---

## 5. Phasen-Gate

M3 gilt als grün, wenn:

1. M3.1 – M3.9 in `00-index.md` auf `[x]`.
2. `terra-engine connect …` läuft 10 min ohne Fehler gegen Hub.
3. Konformitäts-Suite (Negative + Positive) läuft im CI grün.
4. Snapshot-Bundle aus Engine wird vom Hub akzeptiert; in R2 abgelegt;
   Vault zieht den Manifest mit.
5. Tag `v0.4.0` gepusht.

---

## 6. Erledigte Änderungen

— *(noch leer)*

---

*Stand: 2026-05-08 · Greenfield-Initial · M3 noch nicht eröffnet*
