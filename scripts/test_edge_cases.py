#!/usr/bin/env python3
"""Tests two edge cases that the 4 demo scenarios (Normal/Vigilance/
Alert/Critical) do not cover: an incomplete mission reading, and
a RAG query that finds nothing relevant in the corpus.

Goal: prove that the pipeline degrades cleanly (clear message,
no crash, no hallucination fabricated from irrelevant context)
rather than failing silently. Results documented in REPORT.md.

This script is a verification tool, not an automated test in the
pytest sense — human review of the generated text is still needed to
judge whether the model is "inventing" things or not.

Usage: python scripts/test_edge_cases.py
"""

from datetime import date

from src.db import init_db, insert_mission, get_historique
from src.diagnostic import build_prompt, _format_historique, _format_rag_context
from src.llm import generate_diagnostic
from src.models import MissionReading
from src.rag.retrieve import retrieve


def cas_donnee_incomplete() -> None:
    """Mission with 0 zones analyzed (e.g. drone scan interrupted by a
    sensor failure) — tests whether the pipeline handles degenerate data
    (zones_totales=0) without crashing or inventing a percentage."""
    print("=" * 70)
    print("EDGE CASE 1 — incomplete mission reading (0 zones analyzed)")
    print("=" * 70)

    init_db()
    mission = MissionReading(
        mission_id="M-EDGE-001",
        parcelle_id="PARC-EDGE-INCOMPLET",
        date=date(2026, 8, 20),
        culture="Potato",
        stress_ratio=0.0,
        zones_stressees=0,
        zones_totales=0,
        notes="Scan interrupted after 2 minutes of flight — multispectral sensor failure, no zone analyzed.",
    )
    insert_mission(mission)
    historique = get_historique("PARC-EDGE-INCOMPLET")

    print(f"Level computed by the code: {mission.niveau}")
    print(f"Computed stress_pct: {mission.stress_pct}%  (0/0 zones)")

    passages = retrieve("potato water stress 0% thresholds recommendations")
    prompt = build_prompt(mission, historique, passages)
    print("\n--- Prompt sent to the LLM (mission excerpt) ---")
    print(prompt.split("## History")[0])

    result = generate_diagnostic(prompt)
    print("\n--- Generated diagnosis ---")
    print(result.text)
    print(f"\n(latency: {result.latency_s:.1f}s)")


def cas_rag_hors_domaine() -> None:
    """RAG query explicitly outside the corpus's domain
    (wheat fungal disease — the corpus only covers potato water
    stress) — tests whether the LLM flags that the context does not
    cover the question rather than improvising an answer from
    irrelevant passages."""
    print("\n" + "=" * 70)
    print("EDGE CASE 2 — RAG query outside the corpus's domain")
    print("=" * 70)

    requete_hors_domaine = "wheat fungal disease treatment, yellow rust"
    passages = retrieve(requete_hors_domaine)

    print(f"Query: {requete_hors_domaine!r}")
    print("Passages returned by ChromaDB (top-k, no relevance threshold):")
    for p in passages:
        print(f"  - [{p['source']}] distance={p['distance']:.3f}")
        print(f"    {p['text'][:100]}...")

    # Combine these off-topic passages with a real mission, to see
    # whether the LLM misuses them or recognizes that they don't answer
    # the question asked about water stress.
    mission = MissionReading(
        mission_id="M-EDGE-002",
        parcelle_id="PARC-EDGE-RAG",
        date=date(2026, 8, 21),
        culture="Potato",
        stress_ratio=0.45,
        zones_stressees=9,
        zones_totales=20,
        notes="",
    )
    init_db()
    insert_mission(mission)
    historique = get_historique("PARC-EDGE-RAG")
    prompt = build_prompt(mission, historique, passages)

    print("\n--- RAG context injected into the prompt (off-topic, on purpose) ---")
    print(_format_rag_context(passages)[:300], "...")

    result = generate_diagnostic(prompt)
    print("\n--- Generated diagnosis (with an off-topic RAG context) ---")
    print(result.text)
    print(f"\n(latency: {result.latency_s:.1f}s)")


if __name__ == "__main__":
    cas_donnee_incomplete()
    cas_rag_hors_domaine()
