"""Shared data structures for the pipeline.

⚠️ These classes reflect the shape of the data as described in the
specification document (§6.2 NDVI chain). As long as Track B has not
delivered the real extraction of the Idaho dataset, the fields may shift
slightly once the exact structure of the annotations is seen.
"""

from dataclasses import dataclass, field
from datetime import date

from src.config import classify_niveau


@dataclass
class MissionReading:
    """A water stress reading for a given drone mission."""

    mission_id: str
    parcelle_id: str
    date: date
    culture: str
    stress_ratio: float  # 0.0 - 1.0, share of the plot judged stressed
    zones_stressees: int
    zones_totales: int
    notes: str = ""

    @property
    def stress_pct(self) -> float:
        return round(self.stress_ratio * 100, 1)

    @property
    def niveau(self) -> str:
        """Normal / Vigilance / Alert / Critical — computed, not left to the LLM.

        "Insufficient data" if zones_totales == 0 (no zone measured,
        e.g. sensor failure) — distinct from "Normal" (0% stress measured
        on valid zones). See classify_niveau."""
        return classify_niveau(self.stress_ratio, self.zones_totales)


@dataclass
class ParcelleHistorique:
    """History of missions for a plot, sorted from oldest to most recent."""

    parcelle_id: str
    missions: list[MissionReading] = field(default_factory=list)

    def derniere_mission(self) -> MissionReading | None:
        return self.missions[-1] if self.missions else None

    def evolution_stress(self) -> float | None:
        """Delta in percentage points between the last two missions (positive = worsening)."""
        if len(self.missions) < 2:
            return None
        prev, curr = self.missions[-2], self.missions[-1]
        return round(curr.stress_pct - prev.stress_pct, 1)

    def tendance_globale(self) -> str:
        """Trend across the ENTIRE history, not just the last two missions.

        Computed in code for the same reason as `MissionReading.niveau`:
        a test on 08/22 on PARC-03 (58% → 40% → 22%, continuous drop), a
        model still described "a return to a higher level" —
        an invented trend, absent from the figures. By computing it here
        and imposing it in the prompt, we remove the LLM's ability to
        contradict it.
        """
        if len(self.missions) < 2:
            return "insufficient history to establish a trend"
        deltas = [
            round(self.missions[i + 1].stress_pct - self.missions[i].stress_pct, 1)
            for i in range(len(self.missions) - 1)
        ]
        if all(d < 0 for d in deltas):
            return "continuous improvement (drop at every mission)"
        if all(d > 0 for d in deltas):
            return "continuous degradation (rise at every mission)"
        if all(d == 0 for d in deltas):
            return "stable (no change mission to mission)"
        return "fluctuating (neither a continuous rise nor drop across the whole history)"
