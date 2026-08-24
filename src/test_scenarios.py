"""Fait tourner le diagnostic sur PLUSIEURS scénarios de mission, pas un seul.

Couvre les 4 niveaux de la grille de lecture (corpus/seuils_alerte.md) :
normal, vigilance, alerte, critique — plus un cas "sans historique" et un
cas "tendance qui s'améliore" (piège classique : un LLM peut avoir un biais
alarmiste par défaut). Correspond à la tâche Bloc 3 "itérer sur la qualité
des diagnostics" (cahier des charges §7) et au critère de réussite §11
("diagnostics clairs, corrects et actionnables sur plusieurs scénarios").

Fait aussi un contrôle automatique léger (pas un remplacement de la lecture
humaine) : extrait tous les pourcentages mentionnés dans le texte généré et
signale ceux qui ne correspondent à aucune valeur connue (mission courante,
historique, ou seuils de la grille de lecture) — un chiffre qui n'est dans
aucune de ces listes est probablement halluciné.

Usage: python -m src.test_scenarios [--model gemma3:1b]
"""

import argparse
import re
import sqlite3

from src.db import DB_PATH, get_historique, init_db
from src.diagnostic import diagnose

# Seuils de la grille de lecture (corpus/seuils_alerte.md) : légitimes à
# citer même s'ils ne sont pas dans les données de la mission.
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
        print("Aucune parcelle en base. Lancer d'abord : python -m src.seed_data")
        return

    for parcelle_id in parcelles:
        historique = get_historique(parcelle_id)
        mission = historique.derniere_mission()
        attendus = _valeurs_attendues(historique)

        print("=" * 70)
        print(f"Parcelle {parcelle_id} — {mission.culture} — {len(historique.missions)} mission(s) en historique")
        print(f"Stress actuel : {mission.stress_pct}% ({mission.zones_stressees}/{mission.zones_totales} zones)")
        evolution = historique.evolution_stress()
        print(f"Évolution réelle : {evolution if evolution is not None else 'aucun historique antérieur'}")
        print("-" * 70)

        _, result = diagnose(mission, model=model)
        print(result.text)
        print(f"\n(latence : {result.latency_s:.1f}s)")

        suspects = _chiffres_suspects(result.text, attendus)
        if suspects:
            print(f"\n⚠️  Chiffres à vérifier manuellement (absents des données/seuils connus) : {suspects}")
        else:
            print("\n✅ Aucun chiffre suspect détecté (contrôle automatique léger — relire quand même le texte).")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Teste le diagnostic sur plusieurs scénarios de mission")
    parser.add_argument("--model", default=None, help="Modèle Ollama à utiliser (ex: gemma3:1b)")
    args = parser.parse_args()
    run(model=args.model)
