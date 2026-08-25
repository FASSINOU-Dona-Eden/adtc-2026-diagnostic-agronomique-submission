# Project Specification — ADTC 2026 Project
## Mawudo Aerospace × Africa Deep Tech Challenge

**Version:** 3.0 (open point 6 resolved on real data + LLM choice confirmed)
**Date:** August 24, 2026
**Submission deadline:** August 25, 2026

> **Purpose of this document.** Written to be self-sufficient: a team that took part in none of our discussions should be able to read it alone and run the project from A to Z. Every technical term is explained at least once. Every decision is justified so it doesn't get reopened midway through.

> **Continuation of the work after this document (post-migration to the dedicated submission repo).** This document remains the decision journal through Block 5 inclusive. The work to comply with the official ADTC template (`metadata.json`, `download_model.sh`, `model/`, official profiler benchmarks), the robustness tests on edge cases (incomplete data, off-domain RAG — including a fix to `classify_niveau`), and the documented attempt at a West African language summary are recorded directly in **`REPORT.md`** at the repo root, the document required by the ADTC rules.

---

## 1. Context and contest constraint

The Africa Deep Tech Challenge 2026 calls for an application based on a language model (LLM) able to run **entirely offline**, on a **consumer laptop with 8 GB of RAM**, with no dependency on an internet connection or a cloud API.

An **LLM** (Large Language Model) is an AI system trained to understand and produce text. Here, everything must run locally on the machine, with no dedicated GPU and within a limited amount of memory.

The judges' evaluation covers four axes:
1. Model choice and optimization, in particular **quantization** (a technique that compresses a model so it fits in less memory, by reducing the precision of its computations).
2. Memory and latency management (does it fit in 8 GB, does it respond fast enough).
3. Use of **RAG** (local document retrieval — explained in point 4.2).
4. Real-world usefulness of the use case.

---

## 2. Chosen use case

**Post-flight agronomic diagnostic assistant.**

Intended for a field operator (farmer, agronomist) who has just carried out a drone mission over an agricultural plot. The tool takes **already-measured water stress data** (the plants' water-deficit level, expressed as a percentage of affected area) and translates it into a **clear, natural-language diagnosis**, enriched with the history of previous missions on the same plot.

**Key point to understand:** the application does not "look at" photos to judge stress. It receives figures that are already computed, and its job is to **interpret and rephrase** them into useful advice. The reason for this choice is explained in point 3.

---

## 3. Approach tested then discarded (with justification)

> This section is important to keep: it explains **why** the architecture is what it is. In front of the judges, it demonstrates a scientific approach (we tested, measured, decided) rather than an arbitrary choice.

### 3.1 — What was attempted
The initial, more ambitious idea was to use a **VLM** (Vision-Language Model, a model able to "see" an image and talk about it) to directly analyze the drone's aerial photos and judge the visible stress level itself.

### 3.2 — Test protocol
- **6 images** from the scientific dataset *Multispectral Potato Plants Images* (Butte, Vakanski, Duellman et al., 2021 — University of Idaho).
- These 6 images were **deliberately chosen to cover the full annotated spectrum** of stress (from 33% to 85% stressed ratio). Goal: check whether the model can **discriminate** (tell apart) the levels, rather than answering randomly within a comfortable range.
- Comparison with a **human control**: the same images judged blind by a person.

### 3.3 — Results

| Model | Response format | Result |
|---|---|---|
| Gemma 3 4B | Free-form percentage (0-100%) | Responses clustered between 45-65%, no correlation with ground truth |
| Qwen3-VL 8B | Free-form percentage (0-100%) | Responses clustered between 25-30%, no correlation; convergence failures on some images |
| Qwen3-VL 8B | 4-category classification | 1/6 correct (17% agreement with ground truth) |
| Human control | 4-category classification, blind | 4/6 correct (67% agreement) |

**Ground truth** = the true reference answer (here, the annotations established by the researchers in 2021).

### 3.4 — The decision
The vision models available on an 8 GB laptop **are not reliable** for finely discriminating stress from a raw image: they give nearly the same answer regardless of the image. The VLM approach is **discarded**. We switch to a pipeline where stress is pre-computed classically, and where the LLM sticks to interpretation — a task it performs well.

> **Honest nuance worth keeping:** the 2021 ground truth itself is not perfect (a re-review test showed a possible judgment drift over the course of annotation). This nuances the result without invalidating it: the gap between the human control and the models remains clear.

---

## 4. Chosen architecture

The pipeline rests on three components, in this order.

### 4.1 — Mission data processing
Water stress data per zone is obtained through **classical processing** (not generative AI). See point 6 for the exact method (NDVI).

### 4.2 — Local knowledge base (RAG)
**RAG** (Retrieval-Augmented Generation) means: before answering, the system first **searches for relevant information in a local document base**, then supplies it to the model as context. Analogy: instead of answering from memory, the system first checks its notes, then writes.

Two sources are consulted locally, without a connection:
- **History of previous missions** on the same plot (stored locally, structured format). Enables diagnoses like "stress has increased by X% since the last mission."
- **Reference agronomic corpus**: technical sheets on water stress by crop, alert thresholds, standard recommendations.

### 4.3 — Diagnosis generation (local LLM)
The local LLM (candidate: **Gemma 3**) rephrases the quantified data + the context retrieved by RAG into a **clear, actionable, natural-language diagnosis**.

**What the LLM does NOT do:** it never analyzes an image, it learns nothing, it does not compute the stress. It only interprets and writes.

---

## 5. Tech stack

| Component | Choice | Role |
|---|---|---|
| Local inference engine | Ollama (llama.cpp) | Runs the LLM locally |
| Language model | **Gemma 3 4B (`gemma3:4b`), confirmed** | Writes the diagnosis |
| History storage | SQLite | Lightweight local database for mission history |
| Vector search (RAG) | ChromaDB or FAISS | Retrieves relevant corpus passages |
| Language | Python | Glues everything together |
| Demo interface | To be decided: simple CLI or Streamlit | Displays data + diagnosis |

**Vector search:** ChromaDB / FAISS turn the corpus texts into vectors (numeric representations of meaning) to quickly retrieve the passages closest to a query. This is the engine behind RAG.

---

## 6. Decisions made (not to be reopened)

### 6.1 — Data source: Hybrid (real + constructed grouping)

**What the real-dataset analysis showed (08/24).** The *Multispectral Potato Plants* dataset (Supervisely/DatasetNinja format) contains 360 scenes (300 train + 60 test), each with 5 images (RGB 750×750 + Green/Red/Red-Edge/NIR 416×416) and one JSON annotation per image: **bounding boxes per plant**, classified `healthy` or `stressed` — not an already-computed NDVI percentage as assumed in v2.0.

- **Directly usable, at low effort:** the stress ratio per scene (`stressed_boxes / total_boxes`) can be computed in a few lines of Python (`json` stdlib, no heavy dependency). Verified across the 360 scenes: no empty annotation, ratios from 0 to 100%, a distribution that covers the 4 tiers of `corpus/alert_thresholds.md` (5 Normal / 27 Vigilance / 149 Alert / 179 Critical). Median of 14 boxes/scene (3-28), consistent with the `zones_stressees`/`zones_totales` fields already present in `MissionReading`. The raw Red + NIR channels are also present per scene → the bonus NDVI script (§11) remains achievable.
- **Not usable:** no temporal dimension nor plot identifier in the metadata. Each scene is an independent snapshot — the dataset does not allow tracking the same point over time.

**Decision:** the **stress values are real**, extracted from the dataset's annotations (`healthy`/`stressed` counting per image). **Grouping into successive missions on the same plot** (assigned dates, sequencing several real scenes to simulate tracking) is a **demo construct**, since the dataset contains no native longitudinal tracking.

**Why this trade-off rather than a strict Option A or a pure Option B:**
1. Real extraction is trivial and reliable (tested across the 360 scenes) — no reason to ignore it in favor of 100% invented data.
2. Minimal rework effort: only `src/seed_data.py` changes source (hardcoded values → values extracted from the dataset); the SQLite schema, the RAG component, and the generation chain remain unchanged.
3. A strict Option A would require removing the "history / stress evolution" feature (`evolution_stress()`, `tendance_globale()`), already coded and a differentiator for the use case — a real step backward 24 hours before the deadline for a gain in methodological purism.

**Transparency requirement for the submission dossier:** explicitly document that the individual measurements are real (dataset cited), but that their grouping into "several missions on the same plot" is a demonstration construct, not an authentic field time series. Do not let the judges believe it is a real longitudinal tracking.

### 6.1bis — Local LLM model choice: Gemma 3 4B confirmed

**Decision:** keep `gemma3:4b` (already used in `src/config.py`), no model change.

**Reasons:** already validated internally on this specific project — `gemma3:1b` tested and rejected for hallucinating figures absent from the context (3/3 tests); `gemma3:4b` fits within the targeted memory envelope (~4 GB quantized + Python process ~1 GB, reasonable OS margin on 8 GB). The LLM's task is a constrained reformulation (level and trend hardcoded into the prompt, cf. §4.3 — it computes nothing), so there is no need for a larger or more "reasoning-capable" model. Research (08/2026) confirms `gemma3:4b` as a reference for CPU inference on 8 GB; alternatives (Phi-4-mini, Qwen2.5) bring no demonstrated advantage on this specific use case and would introduce a re-validation risk within a tight window.

**Implication:** no change required in `src/llm.py` / `src/diagnostic.py`, already aligned with this choice. The existing `--model` flag (`python -m src.main --model gemma3:1b`) remains available for a one-off comparative test, outside the critical path.

### 6.2 — Where the stress percentages come from: the NDVI chain
A real drone-based water stress reading follows this chain:

1. **Multispectral camera** — captures beyond the visible spectrum (not just Red/Green/Blue), notably the **near-infrared**.
2. **Why infrared:** a well-hydrated plant reflects a lot of infrared; a stressed plant reflects less.
3. **NDVI computation** — **NDVI** (Normalized Difference Vegetation Index) is a formula comparing reflected infrared to reflected red. High value = healthy vegetation; low value = stress.
4. **Thresholding** — the plot is split into zones, NDVI is computed for each, and a cutoff is set below which a zone is "stressed."
5. **Final ratio** — percentage of stressed zones out of the total (e.g., "45% of the plot is stressed").

**What we do:** the dataset's authors have already carried out this entire chain. We retrieve their final percentage directly, without recomputing it.

**Documentation decision:** we state explicitly, in the dossier and in front of the judges, that these values come from an NDVI computation performed by the scientific dataset's authors — a method identical in principle to that of a real multispectral drone.

**Credibility bonus — done on 08/24 (`scripts/compute_ndvi.py`).** Computes NDVI = (NIR - Red) / (NIR + Red) directly on the dataset's raw Red and Near-Infrared channels, per zone (bounding box), for the 9 scenes already used in `src/seed_data.py`. Demonstration purpose (no optimization, no image registration) — applying the formula to raw pixels is enough to prove the method.

**Result: the method validates overall.**
- Average NDVI of zones annotated `healthy`: **0.447** — average NDVI of zones annotated `stressed`: **0.333**. Correct direction (healthy vegetation = higher NDVI), a clear gap between the two groups.
- Thresholding at the midpoint of these two averages (0.390) and comparing, mission by mission, the ratio of zones "stressed according to NDVI" to the ratio of zones "stressed according to annotations" already used for the diagnoses: **correlation r = 0.89** across the 9 scenes, mean absolute gap of **8.7 percentage points**.
- Out of 9 scenes, 7 are close (gap ≤ 12.5 points) — consistent with the idea that NDVI captures the water-stress signal already used in the pipeline reasonably well.

**Notable gap, documented rather than hidden.** Scene `Image_205` (PARC-03, mission of 08/12): annotation ratio 22.2% (2/9 zones), NDVI ratio 0% — a gap of 22.2 points, the largest of the 9. Inspecting the individual zones: the 2 zones annotated `stressed` in this scene have an NDVI of 0.595 and 0.571 — above the global threshold (0.390), and even above several `healthy` zones from other scenes. Plausible explanation: mild or early-stage water stress, visible to the human annotator (likely via visual cues on the RGB image) but not strongly reflected in average NIR/Red reflectance at the whole-zone scale — a known limitation of simple NDVI thresholding versus finer human judgment, consistent with the observation already made in §3 (automated models/methods struggle with early or subtle stress, humans remain sharper on these cases).

**Conclusion for the dossier:** the manual NDVI computation, applied to raw channels, overall recovers the same signal as the annotations already in use (strong correlation), which reinforces the method's credibility — with an honest limitation on mild-stress cases, acknowledged rather than hidden.

---

## 7. Task breakdown (by block)

### Block 1 — Scoping
- [x] Finalize this specification document (NDVI method documented)

### Block 2 — Data & corpus
- [x] Extract stress ratios from the Idaho dataset annotations — *done on 08/24 (`scripts/extract_dataset_stress.py`), hybrid method decided in §6.1: real counting of healthy/stressed bounding boxes per scene*
- [x] Structure the data for the demo — *`src/seed_data.py` rewritten with 9 real missions (4 plots), each value citing its exact source scene*
- [x] Build a coherent mission history for a plot (SQLite) — *unchanged mechanically, data now real*
- [x] Assemble / write the agronomic corpus (crop sheets, thresholds, recommendations) — *reviewed on 08/24: content judged sufficient as-is (consistent with the threshold grid, agronomically plausible — the tuberization stage is well documented for potatoes), no rewrite. "Placeholder to validate" banners replaced with an honest scope note (general agronomic knowledge, not a sourced standard) in the 3 sheets + `corpus/README.md` updated.*
- [x] Vectorize the corpus in ChromaDB / FAISS — *re-ingested on 08/24 with up-to-date data*
- [x] Write the Python NDVI computation script from raw channels (bonus) — *done on 08/24 (`scripts/compute_ndvi.py`), applied to the 9 demo scenes. Result: correlation r = 0.89 with the annotation ratio already in use, mean absolute gap 8.7 points — method validated, detail and nuance in §6.2.*

### Block 3 — Technical pipeline
- [x] Install and configure Ollama + Gemma 3 locally (gemma3:4b chosen, gemma3:1b tested and discarded — hallucinates)
- [x] Build the RAG component (query → vector search → relevant passages)
- [x] Build the generation chain (data + RAG context → prompt → diagnosis)
- [x] Iterate on diagnosis quality — *done on 08/24: the 4 scenarios (Normal/Vigilance/Alert/Critical) generated on real data, `test_scenarios.py`'s automatic check applied to the 4 texts → no suspicious figure detected. Manual review OK (level, trend, and evolution correctly relayed as computed in code, not re-derived by the LLM). Texts saved in `demo/diagnostics_precalcules.md`.*
- [x] **Memory/latency profiling on the 8 GB constraint** — *done on 08/24, on a machine genuinely lacking a dedicated GPU (integrated Intel UHD only — more representative than the initial dev machine). Direct RSS measurement (`ps`) of the `llama-server` process during a real generation: **~3.65 GiB** for `gemma3:4b` (Q4_K_M, pure CPU, `library=cpu` confirmed in the logs) + **~0.81 GiB** for the Python process (embeddings + ChromaDB) = **~4.45 GiB total**, against an 8 GiB budget → **~3.5 GiB margin left for the OS**, constraint respected. Separate point of attention (not a RAM issue): latency measured at **~72-75s per diagnosis** (≈ 8.9 tokens/s in pure-CPU decoding) — to watch for the live demo's pace, independent of the model choice, which remains validated on the memory front.*

### Block 4 — Interface
- [x] Decide CLI vs. Streamlit — *CLI chosen (08/24): already functional, a basic Streamlit wouldn't add enough for the demo in front of a technical jury given the remaining time. A pragmatic decision, not a judgment against Streamlit on principle.*
- [x] Build the display (data + diagnosis + history) — *`src/main.py` enhanced on 08/24: colored level badge (ANSI), full history + trend displayed before generation, consulted RAG sources shown explicitly (visual proof that RAG is actually running). Added `--precalcule`: instant display of an already-generated diagnosis (see `demo/diagnostics_precalcules.json`), for the demo safety net documented in §12/Block 5, without having to manipulate the JSON by hand during the demo.*

### Block 5 — Documentation & demo
- [x] Submission dossier (architecture, justification for discarding the VLM, dataset citation) — *compiled on 08/24 in `docs/submission-dossier.md`, from decisions already made here (no new invented content). Includes architecture, VLM rejection, dataset citation, the real-data/constructed-grouping nuance at the top of a section (§7 of the dossier), proof of compliance with the 8 GB/offline/stability constraints, with measured figures.*
  > ⚠️ **Reminder to include in the dossier's summary, not just in §6.1**: the water stress values are real (extracted from the *Multispectral Potato Plants* dataset's annotations), but their grouping into "successive missions on the same plot" is a demo construct — the dataset contains no longitudinal tracking of the same point over time. This nuance must be visible on a quick read by the judges, not only in the technical detail.
- [ ] Demo scenario in front of the judges
  > ⚠️ **Latency, to be owned if the judges ask about it**: a diagnosis takes ~72-85s in pure CPU generation (measured on 08/24, gemma3:4b, ~8.9 tokens/s decoding). Too slow to chain several live generations without breaking the pace. Mitigation: the 4 demo scenarios (`demo/diagnostics_precalcules.md`) are pre-generated and ready for instant display; **at least one scenario stays generated live during the demo** to prove to the judges that it is not pre-recorded. This is not cheating, it is acknowledged and documented here. The memory risk tied to successive generations (see §12) is now handled structurally in the code, not just through demo discipline — but the transition line below remains useful for pacing, independent of memory stability.
  >
  > **Ready-to-use transition line** (if the judges ask for a 2nd/3rd live diagnosis after the first one): *"I just generated this one live in front of you to show you nothing is pre-recorded. To avoid making you wait a minute every time, I'll show you the results on the other scenarios directly — the mechanism is exactly the same, RAG plus local generation, just displayed without the wait."*
- [ ] Rehearsals under real conditions (target machine)

---

## 8. Constraints to respect

| Constraint | Concrete implication |
|---|---|
| 8 GB of RAM, offline | Test memory profiling **starting in Block 3**, choose Gemma 3's size accordingly. A constraint discovered at D-2 breaks everything. |
| No internet connection | Everything embedded: model, vector store, history, corpus. Nothing calling an API. |
| August 25 deadline | Keep the 25th as margin, don't schedule anything important on it. |
| Mandatory citation | The *Multispectral Potato Plants* dataset (Butte et al., 2021) must be cited in the submission. |

---

## 9. Timeline

| Period | Focus | Note |
|---|---|---|
| Aug 13-14 | Env setup, NDVI doc, corpus scoping | Light |
| Aug 15-16 (weekend) | Data & corpus (Block 2) full push | High availability |
| Aug 17-19 | Technical pipeline (Block 3) starts | Reduced availability for one teammate (McCall MacBain deadline 08/19) → the other takes the technical lead |
| Aug 20-22 | 8 GB profiling + interface (Block 4) | Both fully available |
| Aug 23-24 | Documentation, bonus NDVI script, demo rehearsal | |
| Aug 25 | Margin, final check, submission | Don't schedule anything important |

---

## 10. Two-person organization

| | Track A — technical/pipeline | Track B — data/content/doc |
|---|---|---|
| Ownership | Ollama, RAG, prompt engineering, memory profiling | Agronomic corpus, mission history, submission dossier, NDVI script |
| Logic | Codes the end-to-end chain | Feeds and documents the pipeline |

The two tracks converge on Blocks 4 and 5 (interface + demo).

**Collaboration rules:**
- Short daily sync point (≈15 min), even by message.
- Test against the 8 GB constraint starting in Block 3.
- Keep a decision journal (like this one): internal scoping + material ready for the dossier.
- Rehearse the demo at least twice under real conditions before the day.

---

## 11. Success criteria (definition of done)

The project is "ready to submit" when:
- [ ] The full pipeline runs offline on an 8 GB machine, with no memory overrun.
- [ ] Diagnosis generation latency is acceptable for a live demo.
- [ ] RAG correctly retrieves the history + the corpus and it shows in the diagnosis quality.
- [ ] The generated diagnoses are clear, correct, and actionable across several test scenarios.
- [x] The bonus NDVI script works and produces a ratio consistent with the annotations — *done on 08/24, correlation r = 0.89 across the 9 demo scenes (detail in §6.2).*
- [ ] The submission dossier is complete (architecture, VLM rejection justified, dataset citation).
- [ ] The demo has been rehearsed at least twice on the target machine.

---

## 12. Technical risks and stability notes

### 12.1 — Ollama memory growth on successive generations (resolved, 08/24)

**Observation.** While pre-generating the demo diagnoses (08/24), two `llama-server` crashes were confirmed by the kernel (`journalctl -k`, `Out of memory: Killed process ... (llama-server)`) after several generations in a row within the **same Ollama server session**. RSS measurements of the `llama-server` process (`ps`):
- 1 isolated generation (freshly started server): **~3.65 GiB**, stable.
- 3-4 successive generations, same server, no restart in between: RSS climbs to **~4.3-4.4 GiB**, up to an OOM on a machine already under load otherwise.

**Cause.** Ollama keeps the model loaded in memory between requests (default `keep_alive`: 5 min) and maintains an internal context cache ("context checkpoints," visible in the `llama-server` logs) that grows with each new request as long as the process is not restarted. An isolated diagnosis fits comfortably within the 8 GB budget (§Block 3, profiling), but several diagnoses chained within the same server session are **not** bounded by default.

**Fix implemented (not a demo guideline — a code change).** `src/llm.py::generate_diagnostic()` now passes `keep_alive=0` on every `client.chat()` call: the model is unloaded from RAM immediately after each response, instead of staying loaded. Consequence: every generation now starts from a clean memory state, bounded at ~3.65 GiB, **regardless of how many diagnoses are chained** — the risk is eliminated structurally, not through demo discipline (not chaining too many generations, manually restarting, etc.).

**Cost of the fix.** The model reloads on every call (~10-15s), already absorbed into the measured latency (~72-85s per diagnosis, loading included) — no perceptible extra overhead for the operator.

**Verification.** Reproduced through the real application code path (`src.diagnostic.diagnose()`, not just a raw API call): 3 diagnoses chained across different plots, residual `llama-server` RSS verified at zero after every call (`ps` no longer finds the process), stable latencies (76-85s, no drift).

**What remains true despite the fix:** the demo deliberately plans for a single live generation (see Block 5) for pacing reasons (~75-85s each time), not because memory no longer allows it. The transition line documented in Block 5 serves that pacing, independent of stability — which is now secured.

---

## Appendix — Feasibility test detail

**Protocol:** 6 images from the dataset *Multispectral Potato Plants Images* (Butte, Vakanski, Duellman et al., 2021 — University of Idaho), covering the full annotated stress spectrum (33% to 85%).

**Methodological lesson:** the ground truth (2021 annotations) is probably not perfectly reliable — a possible judgment drift over the course of an annotation session was observed. This nuances the result without invalidating it: the gap between the human control and the tested models remains clear and significant.

**Conclusion:** local vision models available on 8 GB are not reliable for finely discriminating stress from a raw image. Pipeline chosen: pre-quantified data + local LLM limited to interpretation and rephrasing — a task on which these same models perform well.

---

## Quick glossary

- **LLM** — large language model; understands and produces text.
- **VLM** — a model that "sees" an image and talks about it. Discarded here (unreliable on this task).
- **RAG** — the system consults local documents before answering.
- **NDVI** — an index measuring vegetation health via infrared vs. red.
- **Multispectral** — a camera capturing beyond the visible (including infrared).
- **Thresholding** — setting a cutoff to classify a zone as "stressed" or not.
- **Quantization** — compressing a model so it fits in less memory.
- **Vector search** — retrieving texts by semantic proximity (RAG's engine).
- **Ground truth** — the true reference answer used to evaluate a model.
