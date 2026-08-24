# ADTC 2026 — Post-Flight Agronomic Diagnostic Assistant

> **100% offline** LLM application, running on a consumer laptop with **8 GB of RAM**, for the [Africa Deep Tech Challenge 2026](https://www.google.com/search?q=Africa+Deep+Tech+Challenge+2026).

**Mawudo Aerospace** · Submission deadline: **August 25, 2026**

---

## In one sentence

A field operator (farmer, agronomist) returns from a drone mission over a plot. The tool takes their **already-measured water stress data** and turns it into a **clear, natural-language diagnosis**, enriched with the history of previous missions on the same plot — all without any internet connection.

## Why the project is designed this way

An initial approach (feeding aerial photos to a vision model and letting it judge the stress itself) was **tested, then discarded**: vision models available on 8 GB do not reliably discriminate stress level from a raw image. The chosen pipeline therefore relies on **pre-quantified data** (classical NDVI computation), and the local LLM sticks to what it does well: **interpreting and rephrasing**.

Full detail (context, feasibility tests, decisions, timeline) is in the [cahier des charges](docs/cahier-des-charges.md), the internal decision journal. The [dossier de soumission](docs/dossier-de-soumission.md) is its narrative version. **The document required by the ADTC rules** (mandated structure: Problem / Design Decisions / Constraints / Benchmarks, with the profiler's official figures) is [`REPORT.md`](REPORT.md), at the repo root.

## Architecture

The pipeline rests on three components, in this order:

1. **Mission data** — water stress ratio per zone, obtained through classical processing (NDVI), not generative AI.
2. **Local knowledge base (RAG)** — mission history (SQLite) + reference agronomic corpus, consulted without a connection.
3. **Diagnosis generation (local LLM)** — a local model (Gemma 3) rephrases the data + context into an actionable diagnosis.

## Tech stack

| Component | Choice |
|---|---|
| Local inference engine | Ollama (llama.cpp) |
| Language model | Gemma 3 4B (`gemma3:4b`), confirmed |
| History storage | SQLite |
| Vector search (RAG) | ChromaDB |
| Language | Python |
| Demo interface | CLI |

## Repository structure

```
.
├── README.md                    # This file
├── REPORT.md                    # Technical report required by the ADTC template (Problem/Design/Constraints/Benchmarks)
├── metadata.json                # ADTC submission metadata (domain, model, test_prompts)
├── download_model.sh            # Downloads the public .gguf (gemma-3-4b-it Q4_K_M) required by the profiler
├── submission.json              # Output of the official ADTC profiler (real run, see REPORT.md)
├── model/                       # Receives the downloaded .gguf (not versioned, see .gitignore)
├── docs/
│   ├── cahier-des-charges.md        # Full decision journal, with reasoning
│   └── dossier-de-soumission.md     # Narrative version, compiled
├── src/                         # Pipeline code
│   ├── config.py                # Central settings (model, paths, thresholds, classify_niveau)
│   ├── models.py, db.py         # Mission history (SQLite)
│   ├── seed_data.py             # Real data extracted from the dataset (see scripts/)
│   ├── rag/                     # Corpus vectorization + retrieval (ChromaDB)
│   ├── llm.py, diagnostic.py    # Gemma 3 call (Ollama) + prompt assembly
│   ├── main.py                  # Demo CLI (--precalcule for instant display)
│   ├── test_scenarios.py        # Diagnosis test across multiple scenarios
│   └── profiling.py             # RAM/latency measurement
├── scripts/
│   ├── extract_dataset_stress.py    # Extraction of real stress ratios (Idaho dataset)
│   ├── compute_ndvi.py              # Independent NDVI computation on raw channels (bonus, r=0.89 with annotations)
│   ├── test_edge_cases.py           # Robustness tests (incomplete data, off-domain RAG)
│   └── profile_cpu_only.sh          # Profiling forced to CPU (no GPU)
├── demo/                        # Pre-generated diagnoses (demo safety net)
├── data/                        # Mission & history data (not versioned)
├── corpus/                      # Reference agronomic corpus
└── requirements.txt             # Python dependencies (explicit CPU-only torch)
```

## Running the demo

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
ollama pull gemma3:4b

python -m src.seed_data       # mission history (demo data)
python -m src.rag.ingest      # vectorizes the agronomic corpus

python -m src.main --parcelle PARC-01          # one diagnosis (live generation, ~1 min)
python -m src.main --parcelle PARC-04 --precalcule   # instant display (demo safety net)
python -m src.test_scenarios                    # several scenarios at once

PYTHONPATH=. python scripts/test_edge_cases.py   # edge cases (incomplete data, off-domain RAG)
python scripts/compute_ndvi.py                   # independent NDVI validation (requires the raw dataset, see Data)
```

### Checking ADTC template compliance

```bash
bash download_model.sh          # downloads the public .gguf (~2.5 GB)
pip install "git+https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler.git"
adtc-profiler run --submission . --mode participant --output submission.json --skip-accuracy
```

## Data

This project uses the scientific dataset **Multispectral Potato Plants Images**
(Butte, Vakanski, Duellman et al., 2021 — University of Idaho). Water stress ratios
are extracted directly from the original annotations (NDVI computation performed by
the authors), not guessed by a model.

## Status

- ✅ Cahier des charges finalized, open point #6 resolved (Block 1)
- ✅ Real mission data (extracted from the Idaho dataset) and agronomic corpus validated (Block 2)
- ✅ Bonus NDVI script implemented and validated: correlation r = 0.89 with annotations (`scripts/compute_ndvi.py`)
- ✅ End-to-end technical pipeline functional, real data, memory measured and compliant (Block 3)
- ✅ Verified genuinely offline (no external network call, traced via `strace`)
- ✅ Memory stability risk on repeated generations fixed structurally (`keep_alive=0`)
- ✅ Functional CLI interface, with a latency safety net (Block 4)
- ✅ Submission dossier compiled (Block 5) + `REPORT.md` compliant with the official ADTC template
- ✅ Full ADTC submission structure: `metadata.json`, `download_model.sh`, `model/`, official profiler run (`submission.json`) — including thermal throttling, never measured before (none observed)
- ✅ Tested on 2 edge cases (incomplete mission data, off-domain RAG query): clean degradation confirmed. A false negative found (sensor failure classified as "Normal") has been fixed — see `REPORT.md`
- ⚠️ Attempt at a West African language summary (Hausa): tried, abandoned after a confirmed hallucination — honestly documented in `REPORT.md`, not integrated into the product
- ⚠️ Rehearsals under real conditions on the target machine: still to do before submission day

## Team

- **Dona Eden Fassinou** — founder and CEO of Mawudo Aerospace, project architecture
- **Fresnel Satignon** — software engineering student, computer vision / machine learning / deep learning
- **Fifamè Heureuse Fassinou** — recent high-school graduate, Top 20 2026 of Benin's National AI Olympiad

See `REPORT.md` ("Team & Context" section) for the full background.
