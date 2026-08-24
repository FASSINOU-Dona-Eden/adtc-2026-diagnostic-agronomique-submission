"""Populates the SQLite database with a mission history — HYBRID data
(specification §6.1, decision of 08/24): the stress ratios are
REAL, extracted from the *Multispectral Potato Plants* dataset's
annotations (Butte, Vakanski, Duellman et al., 2021 — University of Idaho) via
`scripts/extract_dataset_stress.py`. Each mission below cites its exact
source scene (e.g. "Image_102, train, 2/11 stressed zones").

⚠️ What is NOT real: the grouping of several scenes into "successive
missions on the same plot" (parcelle_id, dates, sequencing). The
dataset contains no longitudinal tracking of the same point over time
(no plot identifier nor capture date in its metadata) —
this construct is a demo device, not to be presented as a genuine
field time series. See also the equivalent note in §6.1 and Block 5
of the specification document.

4 plots covering distinct scenarios (cf. the reading grid in
corpus/seuils_alerte.md), so as not to judge diagnosis quality on
a single case — see src/test_scenarios.py to run them all.

Usage: python -m src.seed_data
"""

from datetime import date

from src.db import init_db, insert_mission
from src.models import MissionReading

MISSIONS_DEMO = [
    # PARC-01: continuous degradation, ends up in the "alert" zone (35-60%).
    # Base case, used to test the "evolution since the last mission"
    # reasoning on a worsening trend.
    MissionReading(
        mission_id="M-2026-06-01",
        parcelle_id="PARC-01",
        date=date(2026, 6, 1),
        culture="Potato",
        stress_ratio=2 / 11,  # Image_102 (train): 2/11 stressed zones
        zones_stressees=2,
        zones_totales=11,
        notes="Start of season, favorable conditions.",
    ),
    MissionReading(
        mission_id="M-2026-07-05",
        parcelle_id="PARC-01",
        date=date(2026, 7, 5),
        culture="Potato",
        stress_ratio=4 / 12,  # Image_103 (train): 4/12 stressed zones
        zones_stressees=4,
        zones_totales=12,
        notes="Dry spell reported locally.",
    ),
    MissionReading(
        mission_id="M-2026-08-15",
        parcelle_id="PARC-01",
        date=date(2026, 8, 15),
        culture="Potato",
        stress_ratio=6 / 11,  # Image_014 (train): 6/11 stressed zones
        zones_stressees=6,
        zones_totales=11,
        notes="Last mission before generating the demo diagnosis.",
    ),
    # PARC-02: a single mission, zero stress ("normal", 0-15%). Tests the
    # "no history available" case (first mission on the plot), on which
    # diagnostic.py must explicitly say there is no computable evolution
    # rather than inventing one.
    MissionReading(
        mission_id="M-2026-08-10",
        parcelle_id="PARC-02",
        date=date(2026, 8, 10),
        culture="Potato",
        stress_ratio=0 / 12,  # Image_101 (train): 0/12 stressed zones
        zones_stressees=0,
        zones_totales=12,
        notes="First mission on this plot, normal conditions.",
    ),
    # PARC-03: improvement after intervention (stress DROPS). Tests
    # whether the LLM recognizes a positive trend and doesn't default to
    # an alarmist tone — a classic pitfall of a prompt too focused on
    # "problems."
    MissionReading(
        mission_id="M-2026-07-01",
        parcelle_id="PARC-03",
        date=date(2026, 7, 1),
        culture="Potato",
        stress_ratio=6 / 10,  # Image_017 (train): 6/10 stressed zones
        zones_stressees=6,
        zones_totales=10,
        notes="High stress detected, targeted irrigation triggered.",
    ),
    MissionReading(
        mission_id="M-2026-07-20",
        parcelle_id="PARC-03",
        date=date(2026, 7, 20),
        culture="Potato",
        stress_ratio=5 / 16,  # Image_255 (train): 5/16 stressed zones
        zones_stressees=5,
        zones_totales=16,
        notes="Improvement after irrigation, to be confirmed.",
    ),
    MissionReading(
        mission_id="M-2026-08-12",
        parcelle_id="PARC-03",
        date=date(2026, 8, 12),
        culture="Potato",
        stress_ratio=2 / 9,  # Image_205 (train): 2/9 stressed zones
        zones_stressees=2,
        zones_totales=9,
        notes="Improvement continuing, situation under control.",
    ),
    # PARC-04: "critical" level (>60%), already high and continuing to
    # degrade fast. Tests the sense of urgency and the immediate
    # intervention recommendation.
    MissionReading(
        mission_id="M-2026-07-28",
        parcelle_id="PARC-04",
        date=date(2026, 7, 28),
        culture="Potato",
        stress_ratio=8 / 14,  # Image_021 (train): 8/14 stressed zones
        zones_stressees=8,
        zones_totales=14,
        notes="Prolonged heat wave reported in the area.",
    ),
    MissionReading(
        mission_id="M-2026-08-14",
        parcelle_id="PARC-04",
        date=date(2026, 8, 14),
        culture="Potato",
        stress_ratio=7 / 9,  # Image_006 (train): 7/9 stressed zones
        zones_stressees=7,
        zones_totales=9,
        notes="Worsening despite partial irrigation.",
    ),
]


def seed() -> None:
    init_db()
    for mission in MISSIONS_DEMO:
        insert_mission(mission)
    parcelles = sorted({m.parcelle_id for m in MISSIONS_DEMO})
    print(f"{len(MISSIONS_DEMO)} missions inserted across {len(parcelles)} plots: {', '.join(parcelles)}.")


if __name__ == "__main__":
    seed()
