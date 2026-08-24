"""Demo CLI: simulates a field operator's return after a drone mission.

Usage:
    python -m src.main                       # last mission of PARC-01
    python -m src.main --parcelle PARC-01
    python -m src.main --parcelle PARC-04 --precalcule   # instant display
                                                            # (demo safety net,
                                                            # see demo/diagnostics_precalcules.json)
"""

import argparse
import itertools
import json
import re
import sys
import threading
import time

from src.config import ROOT_DIR

# src.db / src.diagnostic are NOT imported here but locally inside
# _run_live(): they pull in chromadb/sentence-transformers/torch (~6s
# of import time alone), useless for --precalcule which only reads a
# JSON file. Keeping them at module level would slow down the "instant"
# path for no reason.

# Simple ANSI codes — no external dependency, work in any modern
# terminal (including the ones used for the jury demo).
_COLOR = {
    "Normal": "\033[32m",  # green
    "Vigilance": "\033[33m",  # yellow
    "Alert": "\033[38;5;208m",  # orange
    "Critical": "\033[91m",  # bright red
}
_BOLD = "\033[1m"
_RESET = "\033[0m"

PRECALCULES_PATH = ROOT_DIR / "demo" / "diagnostics_precalcules.json"


def _badge(niveau: str) -> str:
    couleur = _COLOR.get(niveau, "")
    return f"{_BOLD}{couleur}[{niveau.upper()}]{_RESET}"


def _print_historique(historique) -> None:
    if len(historique.missions) <= 1:
        print("History: no previous mission (first mission on this plot).")
        return
    print(f"History ({len(historique.missions)} missions):")
    for m in historique.missions:
        print(f"  {m.date.isoformat()}: {m.stress_pct:>5.1f}%  {_badge(m.niveau)}")
    evolution = historique.evolution_stress()
    if evolution is not None:
        signe = "+" if evolution > 0 else ""
        print(f"  Evolution since the previous mission: {signe}{evolution} points")
    print(f"  Overall trend: {historique.tendance_globale()}")


def _print_sources_rag(prompt: str) -> None:
    sources = sorted(set(re.findall(r"\[Source: ([^\]]+)\]", prompt)))
    if sources:
        print(f"Sources consulted (RAG, agronomic corpus): {', '.join(sources)}")
    else:
        print("Sources consulted (RAG): none (corpus not indexed? run python -m src.rag.ingest)")


def _generer_avec_spinner(mission, model: str | None):
    """Runs diagnose() in a thread while a spinner + counter runs in the
    terminal — without this, ~65-100s of total silence could make
    someone discovering the tool live think it has frozen."""
    from src.diagnostic import diagnose

    resultat: dict = {}

    def _cible():
        try:
            resultat["prompt"], resultat["result"] = diagnose(mission, model=model)
        except Exception as exc:  # noqa: BLE001 — relayed to the main thread below
            resultat["erreur"] = exc

    thread = threading.Thread(target=_cible)
    thread.start()

    spinner = itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
    debut = time.time()
    est_tty = sys.stdout.isatty()
    while thread.is_alive():
        ecoule = time.time() - debut
        if est_tty:
            sys.stdout.write(f"\r  {next(spinner)} generating... {ecoule:4.0f}s ")
            sys.stdout.flush()
        thread.join(timeout=0.15)
    if est_tty:
        sys.stdout.write("\r" + " " * 40 + "\r")
        sys.stdout.flush()
    else:
        # Non-interactive output (redirected log, CI): no useful \r,
        # a single final message is enough to confirm it didn't hang.
        print(f"  (generation finished after {time.time() - debut:.0f}s)")

    if "erreur" in resultat:
        raise resultat["erreur"]
    return resultat["prompt"], resultat["result"]


def _run_live(parcelle_id: str, model: str | None) -> None:
    from src.db import get_historique, init_db

    init_db()
    historique = get_historique(parcelle_id)
    mission = historique.derniere_mission()

    if mission is None:
        print(f"No mission found for plot {parcelle_id}.")
        print("Run first: python -m src.seed_data")
        return

    print("=" * 60)
    print(f"Plot {mission.parcelle_id} — {mission.culture}")
    print(f"Mission of {mission.date.isoformat()}")
    print(
        f"Water stress: {mission.stress_pct}% "
        f"({mission.zones_stressees}/{mission.zones_totales} zones) {_badge(mission.niveau)}"
    )
    print("=" * 60)
    _print_historique(historique)
    print()

    modele = model or "default (see src/config.py)"
    print(f"Generating diagnosis (RAG + local LLM, model: {modele})...")
    print("(~1 min 30 in practice, model loading included — real generation, not pre-recorded)\n")

    prompt, result = _generer_avec_spinner(mission, model)

    _print_sources_rag(prompt)
    print()
    print("--- DIAGNOSIS ---")
    print(result.text)
    print("\n" + "-" * 40)
    print(f"Generation latency: {result.latency_s:.1f}s")


def _run_precalcule(parcelle_id: str) -> None:
    if not PRECALCULES_PATH.exists():
        print(f"No pre-generated diagnosis found ({PRECALCULES_PATH}).")
        print("Use --precalcule only after generating demo/diagnostics_precalcules.json.")
        return

    data = json.loads(PRECALCULES_PATH.read_text(encoding="utf-8"))
    entry = next((e for e in data if e["parcelle"] == parcelle_id), None)
    if entry is None:
        dispo = ", ".join(e["parcelle"] for e in data)
        print(f"No pre-generated diagnosis for {parcelle_id}. Available: {dispo}")
        return

    print("=" * 60)
    print(f"Plot {entry['parcelle']} {_badge(entry['niveau'])} — {entry['stress_pct']}%")
    print(f"({entry['n_missions']} mission(s) in history)")
    print("=" * 60)
    print(f"\n[Pre-generated result from {entry['genere_le']} — {entry['latence_s']}s of generation]\n")
    print("--- DIAGNOSIS ---")
    print(entry["texte"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Post-flight agronomic diagnosis (ADTC 2026)")
    parser.add_argument("--parcelle", default="PARC-01", help="Plot identifier")
    parser.add_argument(
        "--model",
        default=None,
        help="Ollama model to use (e.g. gemma3:1b, gemma3:4b). "
        "Default: the one configured in src/config.py.",
    )
    parser.add_argument(
        "--precalcule",
        action="store_true",
        help="Instantly displays an already-generated diagnosis (demo/diagnostics_precalcules.json) "
        "instead of running a live generation (~1 min). Safety net for the jury demo — "
        "keep at least one scenario generated live to prove it is not pre-recorded.",
    )
    args = parser.parse_args()

    if args.precalcule:
        _run_precalcule(args.parcelle)
    else:
        _run_live(args.parcelle, args.model)


if __name__ == "__main__":
    main()
