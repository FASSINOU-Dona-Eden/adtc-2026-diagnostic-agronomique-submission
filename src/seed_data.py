"""Peuple la base SQLite avec un historique de missions — données HYBRIDES
(cahier des charges §6.1, décision du 24/08) : les ratios de stress sont
RÉELS, extraits des annotations du dataset *Multispectral Potato Plants*
(Butte, Vakanski, Duellman et al., 2021 — University of Idaho) via
`scripts/extract_dataset_stress.py`. Chaque mission ci-dessous cite la scène
source exacte (ex: "Image_102, train, 2/11 zones stressées").

⚠️ Ce qui N'EST PAS réel : le regroupement de plusieurs scènes en "missions
successives sur une même parcelle" (parcelle_id, dates, séquençage). Le
dataset ne contient aucun suivi longitudinal du même point dans le temps
(pas d'identifiant de parcelle ni de date de capture dans ses métadonnées) —
ce montage est une construction de démo, à ne pas présenter comme une vraie
série temporelle terrain. Voir aussi la note équivalente en §6.1 et Bloc 5
du cahier des charges.

4 parcelles couvrant des scénarios distincts (cf. grille de lecture dans
corpus/seuils_alerte.md), pour ne pas juger la qualité des diagnostics sur
un seul cas — voir src/test_scenarios.py pour les faire tourner tous.

Usage: python -m src.seed_data
"""

from datetime import date

from src.db import init_db, insert_mission
from src.models import MissionReading

MISSIONS_DEMO = [
    # PARC-01 : dégradation continue, termine en zone "alerte" (35-60%).
    # Cas de base, sert à tester le raisonnement "évolution depuis la
    # dernière mission" sur une tendance qui empire.
    MissionReading(
        mission_id="M-2026-06-01",
        parcelle_id="PARC-01",
        date=date(2026, 6, 1),
        culture="Pomme de terre",
        stress_ratio=2 / 11,  # Image_102 (train) : 2/11 zones stressées
        zones_stressees=2,
        zones_totales=11,
        notes="Début de saison, conditions favorables.",
    ),
    MissionReading(
        mission_id="M-2026-07-05",
        parcelle_id="PARC-01",
        date=date(2026, 7, 5),
        culture="Pomme de terre",
        stress_ratio=4 / 12,  # Image_103 (train) : 4/12 zones stressées
        zones_stressees=4,
        zones_totales=12,
        notes="Période sèche signalée localement.",
    ),
    MissionReading(
        mission_id="M-2026-08-15",
        parcelle_id="PARC-01",
        date=date(2026, 8, 15),
        culture="Pomme de terre",
        stress_ratio=6 / 11,  # Image_014 (train) : 6/11 zones stressées
        zones_stressees=6,
        zones_totales=11,
        notes="Dernière mission avant génération du diagnostic de démo.",
    ),
    # PARC-02 : une seule mission, stress nul ("normal", 0-15%). Teste le
    # cas "aucun historique disponible" (première mission sur la parcelle),
    # sur lequel diagnostic.py doit explicitement dire qu'il n'y a pas
    # d'évolution calculable plutôt que d'en inventer une.
    MissionReading(
        mission_id="M-2026-08-10",
        parcelle_id="PARC-02",
        date=date(2026, 8, 10),
        culture="Pomme de terre",
        stress_ratio=0 / 12,  # Image_101 (train) : 0/12 zones stressées
        zones_stressees=0,
        zones_totales=12,
        notes="Première mission sur cette parcelle, conditions normales.",
    ),
    # PARC-03 : amélioration après intervention (le stress BAISSE). Teste
    # que le LLM sait reconnaître une tendance positive et ne force pas un
    # ton alarmiste par défaut — piège classique de prompt trop orienté
    # "problème".
    MissionReading(
        mission_id="M-2026-07-01",
        parcelle_id="PARC-03",
        date=date(2026, 7, 1),
        culture="Pomme de terre",
        stress_ratio=6 / 10,  # Image_017 (train) : 6/10 zones stressées
        zones_stressees=6,
        zones_totales=10,
        notes="Stress élevé détecté, irrigation ciblée déclenchée.",
    ),
    MissionReading(
        mission_id="M-2026-07-20",
        parcelle_id="PARC-03",
        date=date(2026, 7, 20),
        culture="Pomme de terre",
        stress_ratio=5 / 16,  # Image_255 (train) : 5/16 zones stressées
        zones_stressees=5,
        zones_totales=16,
        notes="Amélioration après irrigation, à confirmer.",
    ),
    MissionReading(
        mission_id="M-2026-08-12",
        parcelle_id="PARC-03",
        date=date(2026, 8, 12),
        culture="Pomme de terre",
        stress_ratio=2 / 9,  # Image_205 (train) : 2/9 zones stressées
        zones_stressees=2,
        zones_totales=9,
        notes="Poursuite de l'amélioration, situation sous contrôle.",
    ),
    # PARC-04 : niveau "critique" (>60%), déjà élevé et qui continue de
    # se dégrader vite. Teste le ton d'urgence et la recommandation
    # d'intervention immédiate.
    MissionReading(
        mission_id="M-2026-07-28",
        parcelle_id="PARC-04",
        date=date(2026, 7, 28),
        culture="Pomme de terre",
        stress_ratio=8 / 14,  # Image_021 (train) : 8/14 zones stressées
        zones_stressees=8,
        zones_totales=14,
        notes="Vague de chaleur prolongée signalée sur le secteur.",
    ),
    MissionReading(
        mission_id="M-2026-08-14",
        parcelle_id="PARC-04",
        date=date(2026, 8, 14),
        culture="Pomme de terre",
        stress_ratio=7 / 9,  # Image_006 (train) : 7/9 zones stressées
        zones_stressees=7,
        zones_totales=9,
        notes="Aggravation malgré une irrigation partielle.",
    ),
]


def seed() -> None:
    init_db()
    for mission in MISSIONS_DEMO:
        insert_mission(mission)
    parcelles = sorted({m.parcelle_id for m in MISSIONS_DEMO})
    print(f"{len(MISSIONS_DEMO)} missions insérées sur {len(parcelles)} parcelles : {', '.join(parcelles)}.")


if __name__ == "__main__":
    seed()
