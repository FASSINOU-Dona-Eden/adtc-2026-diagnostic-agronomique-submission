"""Profiling mémoire/latence sur la contrainte 8 Go (cahier des charges §8, "à faire tôt").

Mesure la RAM crête (RSS) et la latence de chaque étape du pipeline :
chargement du modèle d'embedding, recherche RAG, génération LLM. Ne
remplace pas un vrai test sur machine cible 8 Go, mais donne un premier
signal sans attendre la fin du projet.

Usage: python -m src.profiling
"""

import resource
import time
from contextlib import contextmanager

from src.db import get_historique, init_db
from src.diagnostic import diagnose
from src.seed_data import seed


def _peak_rss_mb() -> float:
    # ru_maxrss est en Ko sur Linux, en octets sur macOS — on cible Linux
    # (plateforme du jury / laptop grand public visé par le concours).
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


@contextmanager
def _timed(label: str):
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"[{label}] {elapsed:.2f}s — RAM crête cumulée : {_peak_rss_mb():.0f} Mo")


def run_profile(parcelle_id: str = "PARC-01") -> None:
    print("=== Profiling mémoire/latence — pipeline complet ===\n")

    with _timed("Setup DB + seed"):
        init_db()
        seed()

    with _timed("Ingestion corpus (embeddings + Chroma)"):
        from src.rag.ingest import build_index

        build_index()

    with _timed("Diagnostic complet (RAG + génération LLM)"):
        historique = get_historique(parcelle_id)
        mission = historique.derniere_mission()
        _, result = diagnose(mission)

    print(f"\nLatence de génération LLM seule : {result.latency_s:.2f}s")
    print(f"RAM crête (process Python) : {_peak_rss_mb():.0f} Mo")
    print(
        "\nNote : ceci mesure le process Python (embeddings + Chroma), pas le "
        "process Ollama qui héberge le LLM (mémoire séparée, à mesurer via "
        "`ollama ps` pendant la génération). Sur la machine cible 8 Go, "
        "additionner les deux pour valider la contrainte."
    )


if __name__ == "__main__":
    run_profile()
