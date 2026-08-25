# Submission Dossier — Post-Flight Agronomic Diagnostic Assistant

**Mawudo Aerospace × Africa Deep Tech Challenge 2026**
**Compiled on August 24, 2026** from the decisions recorded in `docs/specification.md` (v3.0).

---

## 1. Summary

A field operator (farmer, agronomist) returns from a drone mission over a plot. The tool takes their **already-measured water stress data** and turns it into a **clear, natural-language diagnosis**, enriched with the history of previous missions on the same plot — all **100% offline**, on a consumer laptop with **8 GB of RAM**, with no dedicated GPU.

---

## 2. Context and contest constraint

The Africa Deep Tech Challenge 2026 calls for an application based on a language model (LLM) able to run entirely offline, on a consumer laptop equipped with 8 GB of RAM, with no dependency on an internet connection or a cloud API.

The judges' evaluation covers four axes: model choice and optimization (quantization), memory and latency management, use of RAG (local document retrieval), and the real-world usefulness of the use case. This dossier addresses all four.

## 3. Chosen use case

**Post-flight agronomic diagnostic assistant.** The application does not "look at" photos to judge stress — it receives figures that are already computed (stressed-zone ratio) and its job is to **interpret and rephrase** them into an actionable diagnosis, enriched by local historical and documentary context.

## 4. Approach: what was tested and discarded

An initial, more ambitious approach considered a vision model (VLM) directly analyzing aerial photos to judge the stress level itself. It was **rigorously tested then discarded**, based on measured results — not a hypothesis:

| Model | Response format | Result |
|---|---|---|
| Gemma 3 4B | Free-form percentage (0-100%) | Responses clustered between 45-65%, no correlation with ground truth |
| Qwen3-VL 8B | Free-form percentage (0-100%) | Responses clustered between 25-30%, no correlation; convergence failures on some images |
| Qwen3-VL 8B | 4-category classification | 1/6 correct (17% agreement with ground truth) |
| Human control | 4-category classification, blind | 4/6 correct (67% agreement) |

Protocol: 6 images from the dataset *Multispectral Potato Plants Images* (Butte, Vakanski, Duellman et al., 2021 — University of Idaho), chosen to cover the full annotated stress spectrum (33% to 85%).

**Conclusion:** local vision models available on an 8 GB laptop do not reliably discriminate stress level from a raw image. The approach is discarded in favor of a pipeline where stress is **pre-computed classically**, and where the LLM sticks to interpretation — a task it performs well.

*Honest nuance, owned in front of the judges: the 2021 ground truth itself is not perfect (possible judgment drift over the course of annotation). This nuances the result without invalidating it — the gap between the human control and the tested models remains clear.*

## 5. Chosen architecture

The pipeline rests on three components, in this order:

1. **Mission data processing** — water stress ratio per zone, obtained through classical processing (NDVI chain, §7), not generative AI.
2. **Local knowledge base (RAG)** — two sources consulted locally, without a connection:
   - History of previous missions on the same plot (SQLite) — enables diagnoses like "stress has increased by X points since the last mission."
   - Reference agronomic corpus — sheets on water stress by crop, alert thresholds, irrigation recommendations.
3. **Diagnosis generation (local LLM)** — the model rephrases the quantified data + the RAG context into a clear, actionable diagnosis. **What it does not do**: it never analyzes an image, it learns nothing, it does not compute the stress — it interprets and writes.

## 6. Tech stack

| Component | Choice |
|---|---|
| Local inference engine | Ollama (llama.cpp) |
| Language model | **Gemma 3 4B (`gemma3:4b`)** — see §8 for the justification |
| History storage | SQLite |
| Vector search (RAG) | ChromaDB |
| Embedding model | `all-MiniLM-L6-v2` (lightweight, runs well on CPU/8 GB) |
| Language | Python |
| Demo interface | CLI (see §10) |

## 7. Data source: method and transparency

**What is real.** The water stress values used in the demo are extracted from the annotations of the scientific dataset *Multispectral Potato Plants Images* (Butte, Vakanski, Duellman et al., 2021 — University of Idaho): each scene is annotated with bounding boxes classifying each plant as `healthy` or `stressed`, and the stress ratio is derived directly by counting (`stressed / total`). Reproducible extraction: `scripts/extract_dataset_stress.py`.

**What is constructed for the demo, and must be stated as such.** The dataset contains **no longitudinal tracking of the same point over time** (no plot identifier, no capture date in its metadata). Grouping several real scenes into "successive missions on the same plot" (assigned dates, sequencing) is a **demonstration construct**, not an authentic field time series.

> **To state explicitly to the judges, without waiting to be asked:** the individual stress measurements are real and sourced; their staging into a plot history is a pedagogical construct that demonstrates the RAG "history + evolution" feature, which the dataset alone does not allow illustrating otherwise within the time available.

**Where the percentages come from — the NDVI chain.** A real drone-based water stress reading follows this chain: multispectral camera (captures near-infrared) → a stressed plant reflects less infrared than a healthy one → NDVI computation (an index comparing reflected infrared and red) → per-zone thresholding → final ratio of stressed zones. The dataset's authors carried out this chain; we retrieve their final result (via the `healthy`/`stressed` annotations) without recomputing it — a method identical in principle to that of a real multispectral drone.

**Proof of method mastery.** `scripts/compute_ndvi.py` recomputes NDVI = (NIR - Red)/(NIR + Red) directly on the dataset's raw spectral channels, per zone, for the 9 scenes used in the demo — and compares the result to the annotation ratio already in use. Measured correlation: **r = 0.89** (mean absolute gap 8.7 percentage points), average NDVI of `healthy` zones (0.447) clearly higher than that of `stressed` zones (0.333) — expected direction. One scene deviates notably (mild stress visible to the human annotator, weakly reflected in the zone's average NDVI) — acknowledged and detailed in §6.2 of the specification document rather than hidden.

## 8. LLM model: choice and justification

**`gemma3:4b`, confirmed after direct comparison.** `gemma3:1b` was tested and rejected: it hallucinates figures absent from the provided context (3/3 tests). `gemma3:4b` fits within the targeted memory envelope and demonstrated, once classification and trend were computed in code rather than left to the LLM (§9), reliable rephrasing with no invented figures across the 4 test scenarios (see automatic check, §9).

The task given to the model is a **constrained reformulation** — level and trend already computed and imposed in the prompt, the LLM only interprets and writes — which does not justify a larger or more "reasoning-capable" model. `gemma3:4b` is, moreover, a documented reference for CPU inference on 8 GB of RAM.

## 9. Contest constraints: proof of compliance

**Offline, verified.** `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, ChromaDB telemetry disabled. Verified with `strace -e trace=network` on the full pipeline (ingestion + RAG + generation): a single `connect()`, to `127.0.0.1` (local Ollama). Zero external network calls.

**Memory, genuinely measured — not estimated.** Profiling run on 08/24 on a machine with no dedicated GPU (integrated Intel UHD only), direct RSS measurement (`ps`) of the model process during a real generation:

| Component | Measured RAM |
|---|---|
| `llama-server` (gemma3:4b, Q4_K_M, pure CPU) | ~3.65 GiB |
| Python process (embeddings + ChromaDB) | ~0.81 GiB |
| **Total** | **~4.45 GiB** |
| Remaining margin on the 8 GiB budget | **~3.5 GiB for the OS** |

**Stability under repeated generations, guaranteed structurally.** A memory-growth risk was identified (Ollama's internal context cache grows after several successive generations within the same server session, eventually causing an OOM confirmed by the kernel during testing). Fixed with a code change (`keep_alive=0` on every model call, `src/llm.py`), which unloads the model immediately after each response: every generation starts from a clean memory state (~3.65 GiB), regardless of how many diagnoses are chained during the demo. Full technical detail: `docs/specification.md` §12.

**Latency.** ~72-85s per diagnosis in pure CPU generation (~8.9 tokens/s decoding). Too slow to chain several live generations without breaking a demo's pace — mitigated with pre-generated diagnoses (`demo/diagnostics_precalcules.md`) available for instant display via `python -m src.main --precalcule`, **with at least one scenario staying live-generated** to prove to the judges it is not pre-recorded. Acknowledged and documented, not hidden.

**RAG usage, demonstrated visually.** The demo CLI explicitly displays the corpus sources consulted for each diagnosis, and the plot's full history before generation — the judges see RAG actually working, not just the final result.

**Diagnosis quality.** The 4 test scenarios (Normal / Vigilance / Alert / Critical, real data) were manually reviewed and passed through `test_scenarios.py`'s heuristic check (detection of figures absent from the provided context): no suspicious figure detected across the 4.

## 10. Demo interface

CLI (`python -m src.main --parcelle <ID>`), chosen over a Streamlit interface — marginal gain for the time available in front of a technical jury. Displays: stress level (colored badge), full history and trend, consulted RAG sources, then the generated diagnosis and its real latency.

## 11. Citation

This project uses the scientific dataset **Multispectral Potato Plants Images** (Butte, Vakanski, Duellman et al., 2021 — University of Idaho). Water stress values are extracted directly from the original annotations (`healthy`/`stressed` counting per scene), not guessed by a model. See §7 for the nuance on grouping into plot history.

Source: https://www.webpages.uidaho.edu/vakanski/Multispectral_Images_Dataset.html

## 12. Project status at submission

- ✅ Full pipeline functional offline (real data → RAG → local LLM)
- ✅ 8 GB memory constraint verified by real measurement, and confirmed by the official ADTC profiler (`submission.json`) — including thermal throttling, never measured before (none observed)
- ✅ Memory stability risk identified and fixed structurally
- ✅ Agronomic corpus and mission data validated for the demo
- ✅ Functional CLI interface with a latency safety net
- ✅ Bonus NDVI script (computation from raw Red/NIR channels): implemented, method validated (r = 0.89 with the annotations)
- ✅ Structure compliant with the official ADTC template (`metadata.json`, `download_model.sh`, `model/`, `REPORT.md` at the root)
- ✅ Tested on 2 edge cases (incomplete data, off-domain RAG query) — clean degradation confirmed; a false negative found (sensor failure classified as "Normal") has been fixed (see `REPORT.md`)
- ⚠️ Rehearsals under real conditions on the target machine: still to do before submission day

---

*Document compiled from `docs/specification.md` (v3.0) — refer to it for full decision detail, reasoning, and traceability. The reference document required by the ADTC rules (mandated structure, official profiler benchmarks, robustness tests, West African language attempt) is `REPORT.md` at the repo root — this dossier remains the full narrative version.*
