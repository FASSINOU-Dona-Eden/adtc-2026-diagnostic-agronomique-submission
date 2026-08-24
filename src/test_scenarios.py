"""Runs the diagnosis on SEVERAL mission scenarios, not just one.

Covers the 4 levels of the reading grid (corpus/seuils_alerte.md):
normal, vigilance, alert, critical — plus a "no history" case and a
"improving trend" case (a classic pitfall: an LLM can have a default
alarmist bias). Corresponds to Block 3's "iterate on diagnosis quality"
task (specification §7) and to success criterion §11
("diagnoses that are clear, correct, and actionable across several scenarios").

Also runs a lightweight automatic check (not a replacement for human
review): extracts every percentage mentioned in the generated text and
flags any that do not match a known value (current mission,
history, or the reading grid's thresholds) — a figure that isn't in
any of these lists is probably hallucinated.

Usage: python -m src.test_scenarios [--model gemma3:1b]
"""

import argparse
import re
import sqlite3

from src.db import DB_PATH, get_historique, init_db
from src.diagnostic import diagnose

# Thresholds from the reading grid (corpus/seuils_alerte.md): legitimate to
# cite even if they are not in the mission's data.
SEUILS_CONNUS = {0, 10, 15, 20, 35, 40, 48, 60}


def _parcelles_connues() -> list[str]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT DISTINCT parcelle_id FROM missions ORDER BY parcelle_id").fetchall()
    return [r[0] for r in rows]


def _valeurs_attendues(historique) -> set[float]:
    valeurs = set(SEUILS_CONNUS)
    for m in historique.missions:
        valeurs.add(round(m.stress_pct))
    evolution = historique.evolution_stress()
    if evolution is not None:
        valeurs.add(round(abs(evolution)))
    return valeurs


def _chiffres_suspects(texte: str, attendus: set[float]) -> list[str]:
    trouves = re.findall(r"(\d+(?:[.,]\d+)?)\s*%", texte)
    suspects = []
    for brut in trouves:
        val = round(float(brut.replace(",", ".")))
        if val not in attendus:
            suspects.append(brut)
    return suspects


def run(model: str | None = None) -> None:
    init_db()
    parcelles = _parcelles_connues()
    if not parcelles:
        print("No plot in the database. Run first: python -m src.seed_data")
        return

    for parcelle_id in parcelles:
        historique = get_historique(parcelle_id)
        mission = historique.derniere_mission()
        attendus = _valeurs_attendues(historique)

        print("=" * 70)
        print(f"Plot {parcelle_id} — {mission.culture} — {len(historique.missions)} mission(s) in history")
        print(f"Current stress: {mission.stress_pct}% ({mission.zones_stressees}/{mission.zones_totales} zones)")
        evolution = historique.evolution_stress()
        print(f"Real evolution: {evolution if evolution is not None else 'no prior history'}")
        print("-" * 70)

        _, result = diagnose(mission, model=model)
        print(result.text)
        print(f"\n(latency: {result.latency_s:.1f}s)")

        suspects = _chiffres_suspects(result.text, attendus)
        if suspects:
            print(f"\n⚠️  Figures to check manually (absent from known data/thresholds): {suspects}")
        else:
            print("\n✅ No suspicious figure detected (lightweight automatic check — review the text anyway).")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tests the diagnosis across several mission scenarios")
    parser.add_argument("--model", default=None, help="Ollama model to use (e.g. gemma3:1b)")
    args = parser.parse_args()
    run(model=args.model)
