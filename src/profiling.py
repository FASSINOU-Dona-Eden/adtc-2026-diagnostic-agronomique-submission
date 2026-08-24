"""Memory/latency profiling against the 8 GB constraint (specification §8, "do early").

Measures peak RAM (RSS) and the latency of each pipeline step:
embedding model loading, RAG search, LLM generation. Does not
replace a real test on the 8 GB target machine, but gives an early
signal without waiting until the end of the project.

Usage: python -m src.profiling
"""

import resource
import time
from contextlib import contextmanager

from src.db import get_historique, init_db
from src.diagnostic import diagnose
from src.seed_data import seed


def _peak_rss_mb() -> float:
    # ru_maxrss is in KB on Linux, in bytes on macOS — we target Linux
    # (the jury's platform / the consumer laptop targeted by the contest).
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


@contextmanager
def _timed(label: str):
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"[{label}] {elapsed:.2f}s — cumulative peak RAM: {_peak_rss_mb():.0f} MB")


def run_profile(parcelle_id: str = "PARC-01") -> None:
    print("=== Memory/latency profiling — full pipeline ===\n")

    with _timed("DB setup + seed"):
        init_db()
        seed()

    with _timed("Corpus ingestion (embeddings + Chroma)"):
        from src.rag.ingest import build_index

        build_index()

    with _timed("Full diagnosis (RAG + LLM generation)"):
        historique = get_historique(parcelle_id)
        mission = historique.derniere_mission()
        _, result = diagnose(mission)

    print(f"\nLLM generation latency alone: {result.latency_s:.2f}s")
    print(f"Peak RAM (Python process): {_peak_rss_mb():.0f} MB")
    print(
        "\nNote: this measures the Python process (embeddings + Chroma), not the "
        "Ollama process hosting the LLM (separate memory, to be measured via "
        "`ollama ps` during generation). On the 8 GB target machine, "
        "add the two together to validate the constraint."
    )


if __name__ == "__main__":
    run_profile()
