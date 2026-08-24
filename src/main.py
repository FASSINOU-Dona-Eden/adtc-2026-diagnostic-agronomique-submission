"""CLI de démo : simule le retour d'un opérateur terrain après une mission drone.

Usage:
    python -m src.main                       # dernière mission de PARC-01
    python -m src.main --parcelle PARC-01
    python -m src.main --parcelle PARC-04 --precalcule   # affichage instantané
                                                            # (filet de sécurité démo,
                                                            # voir demo/diagnostics_precalcules.json)
"""

import argparse
import itertools
import json
import re
import sys
import threading
import time

from src.config import ROOT_DIR

# src.db / src.diagnostic ne sont PAS importés ici mais localement dans
# _run_live() : ils tirent chromadb/sentence-transformers/torch (~6s
# d'import à eux seuls), inutiles pour --precalcule qui ne fait que lire
# un JSON. Les garder au niveau module ralentirait "l'instantané" sans
# raison.

# Codes ANSI simples — aucune dépendance externe, fonctionnent dans tout
# terminal moderne (dont ceux utilisés en démo jury).
_COLOR = {
    "Normal": "\033[32m",  # vert
    "Vigilance": "\033[33m",  # jaune
    "Alerte": "\033[38;5;208m",  # orange
    "Critique": "\033[91m",  # rouge vif
}
_BOLD = "\033[1m"
_RESET = "\033[0m"

PRECALCULES_PATH = ROOT_DIR / "demo" / "diagnostics_precalcules.json"


def _badge(niveau: str) -> str:
    couleur = _COLOR.get(niveau, "")
    return f"{_BOLD}{couleur}[{niveau.upper()}]{_RESET}"


def _print_historique(historique) -> None:
    if len(historique.missions) <= 1:
        print("Historique : aucune mission précédente (première mission sur cette parcelle).")
        return
    print(f"Historique ({len(historique.missions)} missions) :")
    for m in historique.missions:
        print(f"  {m.date.isoformat()} : {m.stress_pct:>5.1f}%  {_badge(m.niveau)}")
    evolution = historique.evolution_stress()
    if evolution is not None:
        signe = "+" if evolution > 0 else ""
        print(f"  Évolution depuis la mission précédente : {signe}{evolution} points")
    print(f"  Tendance globale : {historique.tendance_globale()}")


def _print_sources_rag(prompt: str) -> None:
    sources = sorted(set(re.findall(r"\[Source: ([^\]]+)\]", prompt)))
    if sources:
        print(f"Sources consultées (RAG, corpus agronomique) : {', '.join(sources)}")
    else:
        print("Sources consultées (RAG) : aucune (corpus non indexé ? lancer python -m src.rag.ingest)")


def _generer_avec_spinner(mission, model: str | None):
    """Lance diagnose() dans un thread pendant qu'un spinner + compteur
    tourne dans le terminal — sans ça, ~65-100s de silence total peuvent
    faire croire à un plantage à quelqu'un qui découvre l'outil en direct."""
    from src.diagnostic import diagnose

    resultat: dict = {}

    def _cible():
        try:
            resultat["prompt"], resultat["result"] = diagnose(mission, model=model)
        except Exception as exc:  # noqa: BLE001 — relayé au thread principal ci-dessous
            resultat["erreur"] = exc

    thread = threading.Thread(target=_cible)
    thread.start()

    spinner = itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
    debut = time.time()
    est_tty = sys.stdout.isatty()
    while thread.is_alive():
        ecoule = time.time() - debut
        if est_tty:
            sys.stdout.write(f"\r  {next(spinner)} génération en cours... {ecoule:4.0f}s ")
            sys.stdout.flush()
        thread.join(timeout=0.15)
    if est_tty:
        sys.stdout.write("\r" + " " * 40 + "\r")
        sys.stdout.flush()
    else:
        # Sortie non interactive (log redirigé, CI) : pas de \r utile,
        # un seul point final suffit à confirmer que ça n'a pas bloqué.
        print(f"  (génération terminée après {time.time() - debut:.0f}s)")

    if "erreur" in resultat:
        raise resultat["erreur"]
    return resultat["prompt"], resultat["result"]


def _run_live(parcelle_id: str, model: str | None) -> None:
    from src.db import get_historique, init_db

    init_db()
    historique = get_historique(parcelle_id)
    mission = historique.derniere_mission()

    if mission is None:
        print(f"Aucune mission trouvée pour la parcelle {parcelle_id}.")
        print("Lancer d'abord : python -m src.seed_data")
        return

    print("=" * 60)
    print(f"Parcelle {mission.parcelle_id} — {mission.culture}")
    print(f"Mission du {mission.date.isoformat()}")
    print(
        f"Stress hydrique : {mission.stress_pct}% "
        f"({mission.zones_stressees}/{mission.zones_totales} zones) {_badge(mission.niveau)}"
    )
    print("=" * 60)
    _print_historique(historique)
    print()

    modele = model or "défaut (voir src/config.py)"
    print(f"Génération du diagnostic (RAG + LLM local, modèle : {modele})...")
    print("(~1 min 30 en pratique, chargement du modèle compris — génération réelle, pas pré-enregistrée)\n")

    prompt, result = _generer_avec_spinner(mission, model)

    _print_sources_rag(prompt)
    print()
    print("--- DIAGNOSTIC ---")
    print(result.text)
    print("\n" + "-" * 40)
    print(f"Latence de génération : {result.latency_s:.1f}s")


def _run_precalcule(parcelle_id: str) -> None:
    if not PRECALCULES_PATH.exists():
        print(f"Aucun diagnostic pré-généré trouvé ({PRECALCULES_PATH}).")
        print("Utiliser --precalcule uniquement après avoir généré demo/diagnostics_precalcules.json.")
        return

    data = json.loads(PRECALCULES_PATH.read_text(encoding="utf-8"))
    entry = next((e for e in data if e["parcelle"] == parcelle_id), None)
    if entry is None:
        dispo = ", ".join(e["parcelle"] for e in data)
        print(f"Pas de diagnostic pré-généré pour {parcelle_id}. Disponibles : {dispo}")
        return

    print("=" * 60)
    print(f"Parcelle {entry['parcelle']} {_badge(entry['niveau'])} — {entry['stress_pct']}%")
    print(f"({entry['n_missions']} mission(s) en historique)")
    print("=" * 60)
    print(f"\n[Résultat pré-généré le {entry['genere_le']} — {entry['latence_s']}s de génération]\n")
    print("--- DIAGNOSTIC ---")
    print(entry["texte"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnostic agronomique post-vol (ADTC 2026)")
    parser.add_argument("--parcelle", default="PARC-01", help="Identifiant de la parcelle")
    parser.add_argument(
        "--model",
        default=None,
        help="Modèle Ollama à utiliser (ex: gemma3:1b, gemma3:4b). "
        "Par défaut : celui configuré dans src/config.py.",
    )
    parser.add_argument(
        "--precalcule",
        action="store_true",
        help="Affiche instantanément un diagnostic déjà généré (demo/diagnostics_precalcules.json) "
        "au lieu de lancer une génération live (~1 min). Filet de sécurité pour la démo jury — "
        "garder au moins un scénario en génération live pour prouver que ce n'est pas pré-enregistré.",
    )
    args = parser.parse_args()

    if args.precalcule:
        _run_precalcule(args.parcelle)
    else:
        _run_live(args.parcelle, args.model)


if __name__ == "__main__":
    main()
