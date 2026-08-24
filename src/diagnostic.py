"""Chaîne de génération du diagnostic (§4.3) : assemble données + RAG → prompt → LLM."""

from src.config import OLLAMA_MODEL
from src.db import get_historique
from src.llm import GenerationResult, generate_diagnostic
from src.models import MissionReading, ParcelleHistorique
from src.rag.retrieve import retrieve


def _format_historique(historique: ParcelleHistorique, mission_courante: MissionReading) -> str:
    passees = [m for m in historique.missions if m.mission_id != mission_courante.mission_id]
    if not passees:
        return "Aucune mission précédente enregistrée pour cette parcelle."

    lignes = [
        f"- {m.date.isoformat()} : {m.stress_pct}% de stress "
        f"({m.zones_stressees}/{m.zones_totales} zones){' — ' + m.notes if m.notes else ''}"
        for m in passees
    ]
    return "\n".join(lignes)


def _format_rag_context(passages: list[dict]) -> str:
    if not passages:
        return "Aucun passage pertinent trouvé dans le corpus."
    return "\n\n".join(f"[Source: {p['source']}]\n{p['text']}" for p in passages)


def build_prompt(mission: MissionReading, historique: ParcelleHistorique, passages: list[dict]) -> str:
    evolution = historique.evolution_stress()
    evolution_txt = (
        f"{'+' if evolution and evolution > 0 else ''}{evolution} points de %"
        if evolution is not None
        else "non disponible (première mission ou historique insuffisant)"
    )
    tendance = historique.tendance_globale()

    return f"""\
## Mission actuelle
- Parcelle : {mission.parcelle_id}
- Culture : {mission.culture}
- Date : {mission.date.isoformat()}
- Stress hydrique mesuré : {mission.stress_pct}% de la parcelle ({mission.zones_stressees}/{mission.zones_totales} zones)
- Niveau (déjà calculé, à reprendre tel quel) : {mission.niveau}
- Évolution depuis la mission précédente : {evolution_txt}
- Tendance sur tout l'historique (déjà calculée, à reprendre telle quelle) : {tendance}

## Historique des missions précédentes sur cette parcelle
{_format_historique(historique, mission)}

## Extraits pertinents du corpus agronomique (recherche documentaire locale)
{_format_rag_context(passages)}

## Ta tâche
Rédige un diagnostic agronomique pour l'opérateur terrain à partir de ces \
informations. Le niveau et la tendance ci-dessus sont déjà calculés — \
utilise-les tels quels, ne les redéduis pas toi-même depuis le tableau de \
seuils du corpus et ne les contredis pas. Ta rédaction doit couvrir : le \
niveau de stress actuel, la tendance par rapport à l'historique, et une \
recommandation concrète et actionnable en t'appuyant sur les extraits du \
corpus ci-dessus.
"""


def diagnose(mission: MissionReading, model: str | None = None) -> tuple[str, GenerationResult]:
    """Point d'entrée unique : mission → diagnostic texte + métadonnées de génération.

    `model` permet de forcer un modèle Ollama précis (ex: "gemma3:1b") pour
    comparer sans toucher à la config par défaut — voir `python -m src.main --help`.
    """
    historique = get_historique(mission.parcelle_id)

    query = (
        f"stress hydrique {mission.culture} {mission.stress_pct}% "
        f"seuils recommandations irrigation"
    )
    passages = retrieve(query)

    prompt = build_prompt(mission, historique, passages)
    result = generate_diagnostic(prompt, model=model or OLLAMA_MODEL)
    return prompt, result
