"""Central configuration for the ADTC 2026 pipeline.

All the tunable values (model, paths, thresholds) live here to
avoid scattering constants throughout the code.
"""

import os
from pathlib import Path

# --- Strict offline mode ---
# By default, huggingface_hub/sentence-transformers contacts the network on
# every model load to check metadata, EVEN IF the model is already in the
# local cache (~88 MB measured in real traffic during a test with network
# available, for a model that was nonetheless already downloaded).
# Contrary to the contest's "100% offline" constraint (specification §1).
# We force local-cache-only usage — if the model isn't there yet, it fails
# explicitly rather than silently calling the network. Must be set BEFORE
# any import of sentence_transformers / huggingface_hub.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
# ChromaDB sends anonymized telemetry by default (posthog) — another
# silent network leak, config-only, to explicitly disable.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# --- Paths ---
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CORPUS_DIR = ROOT_DIR / "corpus"
DB_PATH = DATA_DIR / "missions.db"
CHROMA_DIR = DATA_DIR / "chroma"

# --- LLM model (Ollama) ---
# Decision made on 08/21 after comparing RAM/latency/reliability: gemma3:1b
# hallucinates figures absent from the provided context (3/3 tests),
# unacceptable for a diagnosis. We keep gemma3:4b despite its higher RAM cost.
OLLAMA_MODEL = "gemma3:4b"
# Overridable via env (useful to point at an isolated test Ollama server,
# e.g. pure-CPU profiling — see scripts/profile_cpu_only.sh).
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# --- RAG ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # lightweight, runs well on CPU/8 GB
CHROMA_COLLECTION = "corpus_agronomique"
RAG_TOP_K = 3

# --- Business thresholds ---
# Level grid — must stay in sync with the table in
# corpus/alert_thresholds.md (adjust together if Track B changes the thresholds).
#
# Computed in code rather than left to the LLM: a test on 4 scenarios
# (08/22) showed gemma3:4b getting the tier wrong by deriving the
# classification itself from the threshold table retrieved by RAG (e.g.
# 75% classified "alert" instead of "critical"). Consistent with the
# specification's rule in §4.3: the LLM interprets, it does not compute —
# classification is a computation, so it is not the LLM's job.
def classify_niveau(stress_ratio: float, zones_totales: int | None = None) -> str:
    """Classifies a stress ratio (0.0-1.0) according to the corpus's threshold grid.

    zones_totales=0 means no zone could be measured at all (e.g. sensor
    failure, interrupted scan) — to be distinguished from "0% stress measured
    on valid zones," which is a genuine "Normal" result. Case discovered and
    documented via scripts/test_edge_cases.py: without this distinction, a
    sensor failure was classified as "Normal" — a potential false negative
    for the operator (a situation perceived as healthy when no reliable
    measurement exists at all). The 4 existing tiers (Normal/Vigilance/Alert/
    Critical) are unchanged for any zones_totales != 0.
    """
    if zones_totales == 0:
        return "Insufficient data"
    if stress_ratio <= 0.15:
        return "Normal"
    if stress_ratio <= 0.35:
        return "Vigilance"
    if stress_ratio <= 0.60:
        return "Alert"
    return "Critical"
