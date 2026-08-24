"""Diagnosis generation chain (§4.3): assembles data + RAG → prompt → LLM."""

from src.config import OLLAMA_MODEL
from src.db import get_historique
from src.llm import GenerationResult, generate_diagnostic
from src.models import MissionReading, ParcelleHistorique
from src.rag.retrieve import retrieve


def _format_historique(historique: ParcelleHistorique, mission_courante: MissionReading) -> str:
    passees = [m for m in historique.missions if m.mission_id != mission_courante.mission_id]
    if not passees:
        return "No previous mission recorded for this plot."

    lignes = [
        f"- {m.date.isoformat()}: {m.stress_pct}% stress "
        f"({m.zones_stressees}/{m.zones_totales} zones){' — ' + m.notes if m.notes else ''}"
        for m in passees
    ]
    return "\n".join(lignes)


def _format_rag_context(passages: list[dict]) -> str:
    if not passages:
        return "No relevant passage found in the corpus."
    return "\n\n".join(f"[Source: {p['source']}]\n{p['text']}" for p in passages)


def build_prompt(mission: MissionReading, historique: ParcelleHistorique, passages: list[dict]) -> str:
    evolution = historique.evolution_stress()
    evolution_txt = (
        f"{'+' if evolution and evolution > 0 else ''}{evolution} percentage points"
        if evolution is not None
        else "not available (first mission or insufficient history)"
    )
    tendance = historique.tendance_globale()

    return f"""\
## Current mission
- Plot: {mission.parcelle_id}
- Crop: {mission.culture}
- Date: {mission.date.isoformat()}
- Measured water stress: {mission.stress_pct}% of the plot ({mission.zones_stressees}/{mission.zones_totales} zones)
- Level (already computed, use as-is): {mission.niveau}
- Evolution since the previous mission: {evolution_txt}
- Trend across the entire history (already computed, use as-is): {tendance}

## History of previous missions on this plot
{_format_historique(historique, mission)}

## Relevant excerpts from the agronomic corpus (local document search)
{_format_rag_context(passages)}

## Your task
Write an agronomic diagnosis for the field operator based on this \
information. The level and the trend above are already computed — \
use them as-is, do not re-derive them yourself from the corpus's \
threshold table, and do not contradict them. Your write-up must cover: \
the current stress level, the trend relative to the history, and a \
concrete, actionable recommendation drawing on the corpus excerpts \
above.
"""


def diagnose(mission: MissionReading, model: str | None = None) -> tuple[str, GenerationResult]:
    """Single entry point: mission → diagnosis text + generation metadata.

    `model` lets you force a specific Ollama model (e.g. "gemma3:1b") to
    compare without touching the default config — see `python -m src.main --help`.
    """
    historique = get_historique(mission.parcelle_id)

    query = (
        f"water stress {mission.culture} {mission.stress_pct}% "
        f"thresholds irrigation recommendations"
    )
    passages = retrieve(query)

    prompt = build_prompt(mission, historique, passages)
    result = generate_diagnostic(prompt, model=model or OLLAMA_MODEL)
    return prompt, result
