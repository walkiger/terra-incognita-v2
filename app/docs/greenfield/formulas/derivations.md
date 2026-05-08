# `formulas/derivations.md` — Schritt-für-Schritt-Herleitungen

> **Zweck.** Für jeden `F.*`-Eintrag, dessen Form nicht direkt aus
> einer Standard­quelle übernommen werden kann (oder dessen
> Implementierungs­form sich von der Bestform unterscheidet), wird
> hier die Herleitung Schritt für Schritt protokolliert. Das ist
> Pflichtmaterial für `verified`-Status und für jede Auditierung
> durch `code-audit-agent` oder `security-code-review-agent`.
>
> Diese Datei ergänzt die Registry (`registry.md`); jeder Abschnitt
> verweist auf die zugehörige `F.*`-ID.

---

## Inhalt

1. [F.LNN.STATE.001 — von der CfC-ODE zur diskreten Update-Form](#1-flnnstate001--von-der-cfc-ode-zur-diskreten-update-form)
2. [F.LNN.STATE.002 — τ-Modulator als saturierende Funktion](#2-flnnstate002--τ-modulator-als-saturierende-funktion)
3. [F.LNN.GROW.001 — Wachstums­formel als Tier-Pyramide](#3-flnngrow001--wachstumsformel-als-tier-pyramide)
4. [F.EBM.ENERGY.002 — KG-projizierte Energie pro Knoten](#4-febmenergy002--kg-projizierte-energie-pro-knoten)
5. [F.EBM.THETA.001 — Adaptiver Schwellenwert als EWMA](#5-febmtheta001--adaptiver-schwellenwert-als-ewma)
6. [F.KG.HEBBIAN.001 — Hebbian-Update mit Tier-Bonus](#6-fkghebbian001--hebbian-update-mit-tier-bonus)
7. [F.REPLAY.HYBRID.001 — Combined-Score-Linearkombination](#7-freplayhybrid001--combined-score-linearkombination)

---

## 1. F.LNN.STATE.001 — von der CfC-ODE zur diskreten Update-Form

### 1.1 Bestform (Hasani 2022, kanonisch)

Die kanonische CfC-Form lautet (Hasani et al., 2022):

\[
\frac{dh(t)}{dt} \;=\; -\frac{h(t)}{\tau(t)} \;+\; f(h(t), x(t)) \cdot g(h(t), x(t))
\]

mit `τ(t)` als zeitabhängiger Time-Constant, `f` als Forget-/Saturations-
Komponente und `g` als Eingangs-Verstärkung.

### 1.2 Schritt 1 — Trennung in linearen und nichtlinearen Anteil

Wir spalten `dh/dt` in einen linearen Term `−h/τ` und den nichtlinearen
Eingangsterm `f·g`. Setzt man `α(t) = 1/τ(t)`, so folgt:

\[
\frac{dh}{dt} = -\alpha h + f g \;\;\Longleftrightarrow\;\; \frac{dh}{dt} + \alpha h = f g.
\]

### 1.3 Schritt 2 — Lösung der inhomogenen ODE über das Integrating-Factor-Verfahren

Mit Integrating-Factor `μ(t) = e^{∫α dt}` ist:

\[
\frac{d}{dt}\big(\mu h\big) = \mu f g
\]

Integrieren von `t` nach `t + Δt` ergibt:

\[
h(t+\Delta t) = h(t)\, e^{-\alpha \Delta t} \;+\; \int_t^{t+\Delta t} e^{-\alpha(t+\Delta t - s)} f(s) g(s)\, ds.
\]

### 1.4 Schritt 3 — Diskretisierung

Wir nehmen `f, g, α` als konstant über das Tick-Intervall `Δt = 1/8 s`.
Damit:

\[
h_{t+1} \;=\; h_t \cdot e^{-\Delta t/\tau} \;+\; \frac{f g}{\alpha}\big(1 - e^{-\Delta t/\tau}\big).
\]

### 1.5 Schritt 4 — Normalisierung in die Code-Form

Der bestehende Code verwendet stattdessen die algebraisch äquivalente
Variante (mit Vorzeichen­wechsel von `g` und Aufteilung):

\[
h_{t+1} \;=\; \frac{(h_t \cdot \exp(-\Delta t/\tau)) - (g \cdot s \cdot f)}{1 + (\Delta t/\tau)\cdot f}.
\]

Hier ist `s` das Self-Signal aus der NCP-Wiring (`F.LNN.STATE.003`).
Die Form ist äquivalent zu Schritt 3, **wenn**

\[
g_{\text{here}} = -\frac{f g_{\text{Hasani}}}{\alpha}, \quad \tau_{\text{here}} = \tau, \quad f_{\text{here}} = f.
\]

Diese Vorzeichen-Konvention ist im Bestand `backend/core/lnn.py`
verankert und wird im Greenfield 1:1 übernommen.

### 1.6 Schritt 5 — Stabilitäts­klemme

Zur Stabilität klemmen wir `τ ∈ [0.05, 5.0]`. Ohne Klemme bei `τ → 0`
wird `exp(-Δt/τ) → 0` (vollständiger Reset), was bei kleinen
Tick-Δt unbeabsichtigte Sprünge erzeugen würde. Bei `τ → ∞` wird
`exp(-Δt/τ) → 1`, was Update-Stillstand verursacht.

### 1.7 Tests

Diese Herleitung ergibt drei Test-Vektoren:

* **Konstanter Eingang**: für `g·s = 0` muss `h_{t+1} = h_t · exp(-Δt/τ)`
  gelten.
* **Stabiler Punkt**: für `h^* = -g·s·f / (1 + (Δt/τ)·f - exp(-Δt/τ))`
  bleibt der State konstant.
* **τ-Klemme**: bei `τ = 1e-6` darf `h_{t+1}` nicht NaN/Inf werden.

Alle drei sind in
`tests/conformance/numerical/test_F_LNN_STATE_conformance.py`.

---

## 2. F.LNN.STATE.002 — τ-Modulator als saturierende Funktion

### 2.1 Anforderung

* `τ` muss positiv bleiben (sonst geht die Update-Form aus §1
  numerisch kaputt).
* `τ` soll input-abhängig sein, damit das System schneller reagiert,
  wenn der Input stark ist.
* `τ` soll beschränkt bleiben (Klemme).

### 2.2 Form

Wir setzen:

\[
\tau(h, u) \;=\; \frac{\tau_0}{1 + \tau_0 \cdot \sigma(W_{th} h + W_{ti} u + b_t)}
\]

mit `σ(z) = 1/(1+e^{-z})`.

### 2.3 Eigenschaften

* `σ(z) ∈ [0, 1]` ⇒ Nenner ∈ `[1, 1 + τ₀]` ⇒ `τ ∈ [τ₀ / (1+τ₀), τ₀]`.
* Bei `τ₀ = 5`: `τ ∈ [5/6 ≈ 0.83, 5]`. Mit anschließender harter
  Klemme erweitern wir auf `[0.05, 5.0]`.
* Monotonie: höherer Aktivierungs­input → kleineres `τ` →
  schnellere Reaktion.

### 2.4 Implementierungs-Form

```python
def tau_modulator(h, u, params):
    z = h @ params.W_th + u @ params.W_ti + params.b_t
    z = sigmoid(z)
    tau = params.tau0 / (1.0 + params.tau0 * z)
    return np.clip(tau, params.tau_min, params.tau_max)
```

### 2.5 Tests

* **Klemmung**: extremer Input → `τ ∈ [τ_min, τ_max]`.
* **Monotonie**: für zwei Inputs `u₁ < u₂` mit identischen Gewichten
  muss `τ(h, u₂) ≤ τ(h, u₁)`.
* **Stetigkeit**: kleiner Input-Δ darf maximal kleine `τ`-Δ erzeugen
  (Lipschitz-Test).

---

## 3. F.LNN.GROW.001 — Wachstums­formel als Tier-Pyramide

### 3.1 Motivation

Wir wollen, dass jede neue Tier-Schicht `n` mehr Channels addiert als
die vorherige; kumulativ ergibt sich eine Pyramide.

### 3.2 Konstruktion

Definiere `Δdim(n)` als Channel-Zuwachs in Tier `n`:

\[
\Delta\dim(n) \;=\; B \cdot n.
\]

Tier 0 hat den Basis-Block `B`. Jeder weitere Tier-`n` fügt `B·n`
hinzu. Aufsummiert:

\[
\dim(N) = B + \sum_{n=1}^{N} B \cdot n = B \cdot \big(1 + \tfrac{N(N+1)}{2}\big).
\]

### 3.3 Tabelle (B = 256)

| N | Σn=1..N (n) | dim(N)  |
|---|------------:|--------:|
| 0 | 0           | 256     |
| 1 | 1           | 512     |
| 2 | 3           | 1024    |
| 3 | 6           | 1792    |
| 4 | 10          | 2816    |
| 5 | 15          | 4096    |

### 3.4 Konsequenz

Bei jedem `_on_tier_stable(n)`-Trigger wird `lnn.grow()` aufgerufen,
das Hidden-State und Input-Vektor auf `dim(N)` ausweitet. `hD = iD`
bleibt invariant (`Anweisungen.md` §7).

---

## 4. F.EBM.ENERGY.002 — KG-projizierte Energie pro Knoten

### 4.1 Ausgangsform (Hopfield)

\[
E(\mathbf{x}) = -\tfrac{1}{2} \mathbf{x}^\top W \mathbf{x} - b^\top \mathbf{x}.
\]

### 4.2 Per-Knoten-Auswertung

Wir interessieren uns für die marginale Energie eines einzelnen Knotens
`v` bei gegebener Restaktivität `a`:

\[
E_{\text{node}}(v) = -\sum_{u \neq v} W_{vu} a_v a_u - b_v a_v - \tfrac{1}{2} W_{vv} a_v^2.
\]

Mit `a_v ∈ {0,1}` (binäre Variante; in unserer Implementierung später
weich auf `[0,1]` erweitert) und `W_{vv} = 0` (keine Selbst­schleifen
in der KG-Topologie) reduziert sich dies zu:

\[
E_{\text{node}}(v) = -a_v \cdot \big(\sum_{u \in N(v)} W_{vu} a_u + b_v\big).
\]

### 4.3 Vereinfachung

Bei `a_v = 1` (aktiver Knoten):

\[
E_{\text{node}}(v) = -\sum_{u \in N(v)} W_{vu} a_u - b_v.
\]

Diese Form steht in `registry.md` und ist die Implementierungs-Basis
in `backend/core/ebm.py::node_energy`.

### 4.4 Konsequenz für Wells

Ein Knoten ist Well-Kandidat, wenn `E_node(v) < θ` über ein
Stabilitäts­fenster (siehe `F.EBM.WELL.001`). Damit wird die Wahl der
Nachbar­knoten und der Kanten­gewichte zur dominanten Stellschraube für
Tier-Stabilität — was wiederum erklärt, warum die `F.KG.HEBBIAN.*`-
Updates so vorsichtig sein müssen (`top-6` mit Tier-Bonus, `bottom-12`
nur Decay).

---

## 5. F.EBM.THETA.001 — Adaptiver Schwellenwert als EWMA

### 5.1 Ziel

`θ` (Well-Birth-Schwelle) soll dem aktuellen Energie-Niveau folgen, ohne
zu zappeln. Das ist klassisch ein EWMA-Filter.

### 5.2 Update-Form

\[
\theta_{t+1} = \theta_t + \kappa \cdot (\bar E_t - \theta_t)
\]

mit `κ = ebm_theta_lr ∈ (0, 1)`, default `0.01`. Der Gleitmittel­anteil
`\bar E_t` wird über die letzten `K` (default 256) Tick-Energien
berechnet.

### 5.3 Stabilitäts­bedingung

Damit `θ` nicht oszilliert, muss `κ` klein gegenüber der typischen
Änderungs­rate von `\bar E_t` sein. Empirisch: `κ ≤ 0.05`, default
`0.01` lässt `θ` mit ca. 100 Ticks Verzögerung folgen → entspricht
~12.5 s realer Zeit. Das ist in der Zielgrößenordnung
(„Stabilitätsfenster" ist 1–60 s je Tier).

---

## 6. F.KG.HEBBIAN.001 — Hebbian-Update mit Tier-Bonus

### 6.1 Klassische Hebb-Regel

\[
\Delta W_{ij} = \eta \cdot a_i \cdot a_j
\]

(„fire together, wire together"). In unserer Implementierung wirken
`(a_i, a_j) ∈ \{0, 1\}` über die Top-`K`-Auswahl (`top-6` Knoten nach
`_lnnFocus`), damit nur die fokussierten Knoten Update bekommen.

### 6.2 Tier-Bonus

Damit höhere Tiers nicht von immer weiter wachsenden niedrigeren Tiers
verdrängt werden, addieren wir einen multiplikativen Bonus:

\[
\Delta W_{ij} = \eta \cdot b_{\text{tier}}(t_i, t_j), \quad b_{\text{tier}}(t_i, t_j) = 1 + 0.5 \cdot \max(t_i, t_j).
\]

### 6.3 Klemmung

Damit Gewichte bounded bleiben (`W_{ij} \in [0, 1]`), klemmen wir nach
jedem Update. Die Top-6-Auswahl + die Klemmung stellen sicher, dass das
KG nicht in Richtung „alles mit allem verbunden" entartet.

### 6.4 Decay

Die Bottom-12-Knoten (kein Fokus) erhalten parallel einen kleinen
Decay-Schritt (`F.KG.HEBBIAN.002`):

\[
\Delta W_{ij} = -\delta, \quad \delta = 0.0005.
\]

### 6.5 Pruning

Kanten unter `W_min` werden nach `τ_stable`-Stabilität entfernt
(`F.KG.HEBBIAN.003`). Damit bleibt das KG schlank, ohne dass kürzlich
gebildete Kanten vorschnell weggeschnitten werden.

---

## 7. F.REPLAY.HYBRID.001 — Combined-Score-Linearkombination

### 7.1 Motivation

Die Replay-Suche soll BM25 (klassischer FTS-Score) und einen einfachen
Substring-Hit-Counter linear kombinieren — mit User-justierbaren
Gewichten `α` und `β`.

### 7.2 Normalisierung von BM25

BM25 ist unbegrenzt; wir benutzen die klassische
`bm25 / (bm25 + 1)`-Normalisierung, die einen Score in `[0, 1)` liefert:

\[
\text{bm25}_{\text{norm}} = \frac{\text{bm25}}{\text{bm25} + 1}.
\]

### 7.3 Hits-Normalisierung

`hits` ist eine kleine Ganzzahl (0..3) je nach Übereinstimmungsgrad
(`word ⊂ q`, `meta.text ⊂ q`, `word == q`). Wir normalisieren
linear:

\[
\text{hits}_{\text{norm}} = \frac{\text{hits}}{3}.
\]

### 7.4 Linearkombination

\[
\text{combined} = \alpha \cdot \text{bm25}_{\text{norm}} + \beta \cdot \text{hits}_{\text{norm}}.
\]

`α + β` ist nicht zwangsweise `1` — der User darf Gewichte heraus­
heben, dann ergibt der Score auch Werte > 1 oder < 1. Sortierung
erfolgt deterministisch nach `combined DESC, ts_ms DESC, id ASC`.

### 7.5 Test-Vektoren

* `bm25 = 0, hits = 0` → `combined = 0`.
* `bm25 = 0, hits = 3` → `combined = β`.
* `bm25 = 1, hits = 0` → `combined = α / 2`.
* `bm25 = 1, hits = 3` → `combined = α / 2 + β`.

Diese vier Punkte werden in `tests/db/test_replay_query.py::
test_F_REPLAY_HYBRID_001_corner_points` direkt geprüft.

---

*Stand: 2026-05-08 · Greenfield-Initial · Begleit­dokument zu
`registry.md` für `verified`-Status.*
