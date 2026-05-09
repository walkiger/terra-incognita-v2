# Design Session — Briefing (terra-055 corpus + Kontext)

**Stand:** 2026-05-07  
**Korpus:** 17 PDFs mit L0–L4 unter `research/extracted/*_20260507T081859Z/` (Batch terra-055).  
**Zusätzlicher Kontext:** 6 Papers aus terra-052 (PR #46), L1–L4 unter `research/extracted/*_20260507T000032Z/`.

**Machine-Read Anchors:** `research/work/terra055_page_anchors_20260507.json` (Seite + Locator pro Dokument).

---

## 1) Ziel der Session (90 min)

Aus dem Research-Korpus **4–8 bindende Design-Entscheidungen** für das Drei-Pol-System (LNN ↔ EBM ↔ KG) ableiten, mit:

- klarer **Option** pro Frage,
- **Evidenzgrad** (hoch = direkter PDF-Treffer; mittel/niedrig = Overlap/Excerpt),
- expliziten **Gaps**, wo nur Intro/Abstract abgedeckt ist.

**Nicht-Ziele:** Implementierung, PR-Merge, Backend-API-Detail bis Contract vorliegt.

---

## 2) Evidenzregeln (5 min zu Beginn festhalten)

| Label | Bedeutung |
|-------|-----------|
| **H** | Locator steht wörtlich auf angegebener PDF-Seite (Titelzeile / Abstract / direkter Phrase-Match). |
| **M** | token_overlap / L4-Zusammenfassung passt zu Seite; manuell im PDF verifizieren. |
| **L** | schwacher Overlap; nur als Hypothese, nicht als „Citation closed“. |

**Canonical paths:** PDF `research/incoming/<slug>.pdf`, Extraktion `research/extracted/<slug>/l4_analysis.json`.

---

## 3) Agenda (90 min)

| Min | Block | Inhalt |
|-----|--------|--------|
| 0–10 | Regeln | Evidenz H/M/L, Gap-Honesty |
| 10–25 | Q1–Q2 | KG-Encoder, Skalierung |
| 25–45 | Q3–Q4 | LM↔KG-Fusion, Retrieval/Ranking |
| 45–65 | Q5–Q6 | EBM/Unsicherheit, logische Queries |
| 65–80 | Q7–Q8 | Energie/Benchmarks |
| 80–90 | Output | Decisions.md-Stichpunkte, offene Follow-ups |

---

## 4) Acht Entscheidungsfragen + PDF-Verweise

### Q1 — Primärer KG-Encoder-Stil

**Frage:** Welches Encoder-Paradigm priorisieren wir für relationale Nachbarschaft (vor Decoder/Scoring)?

**Optionen:** R-GCN / relation-weighted (SACN-artig) / GAT / explizit hybrid ab Tier.

**Primärquellen (Anker aus `terra055_page_anchors_20260507.json`):**

| document_id (Suffix …081859Z) | PDF (Repo-Pfad) | Seite | Locator (Suche im PDF) | Evidenz |
|-------------------------------|-------------------|-------|-------------------------|---------|
| `a_survey_on_graph_neural_networks_for_knowledge_graph_completion_…` | `research/incoming/a_survey_on_graph_neural_networks_for_knowledge_graph_completion_20260507T081859Z.pdf` | 1 | „A Survey on Graph Neural Networks for Knowledge Graph Completion“ | H |
| `published_as_a_conference_paper_at_iclr_2018_graph_attention_networks_pe_…` | `research/incoming/published_as_a_conference_paper_at_iclr_2018_graph_attention_networks_pe_20260507T081859Z.pdf` | 1 | „GRAPH ATTENTION NETWORKS“ | H |
| `graph_convolutional_networks_a_comprehensive_review_si_zhang1_introducti_…` | `research/incoming/graph_convolutional_networks_a_comprehensive_review_si_zhang1_introducti_20260507T081859Z.pdf` | 1 | „Abstract … Graphs naturally appear…“ | H |

**Deep dive Artefakt:** `research/extracted/<slug>/l4_analysis.json` (pro Paper „key_points“ / Framing).

**Gap:** Feintuning (welches Modul bei |R| groß) braucht ggf. Volltextseiten jenseits Intro — in Session als „Follow-up: Seiten x–y verifizieren“ markieren.

---

### Q2 — Skalierung bei großem Relationenraum

**Frage:** Basisdecomposition vs dichte relation-spezifische Parameter — wo liegt unsere Default-Hypothese?

**Primärquellen:**

| document_id | PDF | Seite | Locator | Evidenz |
|-------------|-----|-------|---------|---------|
| `a_survey_on_graph_neural_networks_for_knowledge_graph_completion_…` | …`a_survey…081859Z.pdf` | 1 | Titel + Survey-Rahmen KGC | H |
| `graph_convolutional_networks_a_comprehensive_review_si_zhang1_introducti_…` | …`graph_convolutional…081859Z.pdf` | 1 | Abstract Einleitung | H |

---

### Q3 — LM ↔ KG Fusion (Pretraining / joint reasoning)

**Frage:** Welches Fusionsmuster ist für Encounter-synchrones Reasoning am nächsten (nicht: welches Paper „gewinnt“, sondern welches **Interface** wir nachbauen)?

**Primärquellen:**

| document_id | PDF | Seite | Locator | Evidenz |
|-------------|-----|-------|---------|---------|
| `deep_bidirectional_language_knowledge_graph_pretraining_…` | …`deep_bidirectional…081859Z.pdf` | 1 | „Deep Bidirectional Language-Knowledge Graph Pretraining“ | H |
| | | 3 | „DRAGON combines… MLM + link prediction“ (M) | M |
| `published_as_a_conference_paper_at_iclr_2022_grease_lm_g_raph_reas_oning_…` | …`grease_lm…081859Z.pdf` | 1 | „GREASE LM… QUESTION ANSWERING“ | H |
| `proceedings_of_the_2021_conference_of_the_north_american_chapter_of_the_…` | …`proceedings_of_the_2021…081859Z.pdf` | 1 | „pages 535–546“ + QA-GNN | H |

---

### Q4 — Retrieval / Ranking vor Generierung

**Frage:** Ist eine explizite Ranking-/Reranking-Stufe (KG oder Text) Pflicht vor LLM-Antwort?

**Primärquelle:**

| document_id | PDF | Seite | Locator | Evidenz |
|-------------|-----|-------|---------|---------|
| `proceedings_of_the_23rd_workshop_on_biomedical_language_processing_pages_…` | …`proceedings_of_the_23rd…081859Z.pdf` | 1 | „KG-Rank… Medical QA… Knowledge Graphs and Ranking“ | H |

---

### Q5 — EBM-Schicht: klassisch vs graphische Energie / Uncertainty

**Frage:** Wo sitzt „Energie“ im System: klassisches EBM-Training (Sampling) vs GEBM-Multi-Skala vs nur als Uncertainty-Head?

**Primärquellen:**

| document_id | PDF | Seite | Locator | Evidenz |
|-------------|-----|-------|---------|---------|
| `implicit_generation_and_modeling_with_energy_based_models_yilun_du_mit_c_…` | …`implicit_generation…081859Z.pdf` | 1 | „Implicit Generation… Energy-Based Models“ | H |
| `energy_based_epistemic_uncertainty_for_graph_neural_networks_…` | …`energy_based_epistemic…081859Z.pdf` | 1 | Titel „Energy-based Epistemic Uncertainty…“ | H |
| | | 4 | „GEBM builds… independent, local, and group energy…“ | M |

---

### Q6 — Logische Queries auf dem KG

**Frage:** Welche Operator-/Query-Klasse ist v1-Minimum (Conjunction/Negation/Difference, etc.)?

**Primärquellen:**

| document_id | PDF | Seite | Locator | Evidenz |
|-------------|-----|-------|---------|---------|
| `neural_answering_logical_queries_on_knowledge_graphs_…` | …`neural_answering_logical…081859Z.pdf` | 1 | „Neural-Answering Logical Queries…“ | H |
| `published_as_a_conference_paper_at_iclr_2022_neural_methods_for_logical_…` | …`neural_methods_for_logical…081859Z.pdf` | 1 | „NEURAL METHODS FOR LOGICAL REASONING…“ | H |

---

### Q7 — Energie / Kosten (Inferenzpfad)

**Frage:** KG-augmentiert vs Vektor-Retrieval — wann welcher Pfad Default, welche Metrik (Latenz, Wh, CO2eq als Zielgröße)?

**Primärquelle:**

| document_id | PDF | Seite | Locator | Evidenz |
|-------------|-----|-------|---------|---------|
| `towards_energy_aware_requirements_dependency_classification_knowledge_gr_…` | …`towards_energy_aware…081859Z.pdf` | 1 | „Knowledge-Graph vs. Vector-Retrieval… SLMs“ | H |

---

### Q8 — Benchmark-Priorität für Design-Validierung

**Frage:** Welche 2–3 Benchmarks/Tasks reichen für Phase-1-Designfreeze?

**Primärquellen:**

| document_id | PDF | Seite | Locator | Evidenz |
|-------------|-----|-------|---------|---------|
| `commonsense_qa_a_question_answering_challenge_targeting_…` | …`commonsense_qa…081859Z.pdf` | 1 | „COMMONSENSE QA…“ | H |
| `can_a_suit_of_armor_conduct_electricity_a_new_dataset_for_open_book_ques_…` | …`can_a_suit…081859Z.pdf` | 1 | OpenBookQA-Titel | H |
| | | 2 | OpenBookQA retrieval-and-reasoning bottleneck (M) | M |
| `what_to_pre_train_on_ef_cient_intermediate_task_selection_…` | …`what_to_pre_train…081859Z.pdf` | 1 | „Efficient Intermediate Task Selection“ | H |

**Cross:** `arxiv_2307_08411v1…neurosymbolic…` — biomedical KG survey angle (S.1 H, ggf. S.6 L für Motivation).

---

## 5) terra-052 (6 Papers) — Kurzverweis

Für die Session **optional** einbeziehen (bereits L1–L4, PR #46):

- Slugs enden auf `_20260507T000032Z` unter `research/extracted/`.
- Implementierungs-Notizen: `archive/legacy-docs/Implementierung.research.l0_to_l4.md` (Root), sofern Branch gemerged.

**Nutzen:** Abgleich „Batch-Qualität“ terra-052 vs terra-055; keine neuen Seitenanker-Pflicht, wenn Zeit knapp.

---

## 6) Session-Output (Vorlage)

Pro Q1–Q8 festhalten:

- **Entscheidung:** A / B / Hybrid + ein Satz.
- **Evidenz:** H/M/L + PDF + Seite.
- **Gap:** was nach der Session nachgelesen werden muss.
- **Owner:** wer schreibt Contract-Skizze (orch / documentation follow-up).

---

## 7) Referenzdateien (Copy-Paste)

- Anker-JSON: `research/work/terra055_page_anchors_20260507.json`
- Sweep-Skript (Repro): `research/work/terra055_page_anchor_sweep.py`

---

_Ende Briefing_
