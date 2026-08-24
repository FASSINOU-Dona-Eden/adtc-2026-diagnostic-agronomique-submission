"""Structures de données partagées par le pipeline.

⚠️ Ces classes reflètent la forme des données telles que décrites dans le
cahier des charges (§6.2 chaîne NDVI). Tant que Piste B n'a pas livré
l'extraction réelle du dataset Idaho, les champs peuvent bouger légèrement
une fois qu'on voit la structure exacte des annotations.
"""

from dataclasses import dataclass, field
from datetime import date

from src.config import classify_niveau


@dataclass
class MissionReading:
    """Un relevé de stress hydrique pour une mission drone donnée."""

    mission_id: str
    parcelle_id: str
    date: date
    culture: str
    stress_ratio: float  # 0.0 - 1.0, part de la parcelle jugée stressée
    zones_stressees: int
    zones_totales: int
    notes: str = ""

    @property
    def stress_pct(self) -> float:
        return round(self.stress_ratio * 100, 1)

    @property
    def niveau(self) -> str:
        """Normal / Vigilance / Alerte / Critique — calculé, pas laissé au LLM."""
        return classify_niveau(self.stress_ratio)


@dataclass
class ParcelleHistorique:
    """Historique des missions pour une parcelle, trié du plus ancien au plus récent."""

    parcelle_id: str
    missions: list[MissionReading] = field(default_factory=list)

    def derniere_mission(self) -> MissionReading | None:
        return self.missions[-1] if self.missions else None

    def evolution_stress(self) -> float | None:
        """Delta en points de % entre les deux dernières missions (positif = ça empire)."""
        if len(self.missions) < 2:
            return None
        prev, curr = self.missions[-2], self.missions[-1]
        return round(curr.stress_pct - prev.stress_pct, 1)

    def tendance_globale(self) -> str:
        """Tendance sur TOUT l'historique, pas juste les deux dernières missions.

        Calculée en code pour la même raison que `MissionReading.niveau` :
        test du 22/08 sur PARC-03 (58% → 40% → 22%, baisse continue), un
        modèle a quand même décrit "un retour vers un niveau plus élevé" —
        une tendance inventée, absente des chiffres. En la calculant ici et
        en l'imposant dans le prompt, on retire au LLM la possibilité de la
        contredire.
        """
        if len(self.missions) < 2:
            return "historique insuffisant pour dégager une tendance"
        deltas = [
            round(self.missions[i + 1].stress_pct - self.missions[i].stress_pct, 1)
            for i in range(len(self.missions) - 1)
        ]
        if all(d < 0 for d in deltas):
            return "amélioration continue (baisse à chaque mission)"
        if all(d > 0 for d in deltas):
            return "dégradation continue (hausse à chaque mission)"
        if all(d == 0 for d in deltas):
            return "stable (aucun changement mission à mission)"
        return "fluctuante (ni hausse ni baisse continue sur tout l'historique)"
