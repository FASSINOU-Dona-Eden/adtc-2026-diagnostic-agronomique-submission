#!/usr/bin/env python3
"""Teste deux cas limites que les 4 scénarios de démo (Normal/Vigilance/
Alerte/Critique) ne couvrent pas : une donnée de mission incomplète, et
une requête RAG qui ne trouve rien de pertinent dans le corpus.

Objectif : prouver que le pipeline dégrade proprement (message clair,
pas de plantage, pas d'hallucination fabriquée à partir d'un contexte
non pertinent) plutôt que d'échouer silencieusement. Résultats
documentés dans REPORT.md.

Ce script est un outil de vérification, pas un test automatisé au sens
pytest — la lecture humaine du texte généré reste nécessaire pour juger
si le modèle "invente" ou pas.

Usage : python scripts/test_edge_cases.py
"""

from datetime import date

from src.db import init_db, insert_mission, get_historique
from src.diagnostic import build_prompt, _format_historique, _format_rag_context
from src.llm import generate_diagnostic
from src.models import MissionReading
from src.rag.retrieve import retrieve


def cas_donnee_incomplete() -> None:
    """Mission avec 0 zone analysée (ex: scan drone interrompu par une
    panne capteur) — teste si le pipeline gère une donnée dégénérée
    (zones_totales=0) sans planter ni inventer un pourcentage."""
    print("=" * 70)
    print("CAS LIMITE 1 — donnée de mission incomplète (0 zone analysée)")
    print("=" * 70)

    init_db()
    mission = MissionReading(
        mission_id="M-EDGE-001",
        parcelle_id="PARC-EDGE-INCOMPLET",
        date=date(2026, 8, 20),
        culture="Pomme de terre",
        stress_ratio=0.0,
        zones_stressees=0,
        zones_totales=0,
        notes="Scan interrompu après 2 minutes de vol — panne capteur multispectral, aucune zone analysée.",
    )
    insert_mission(mission)
    historique = get_historique("PARC-EDGE-INCOMPLET")

    print(f"Niveau calculé par le code : {mission.niveau}")
    print(f"stress_pct calculé : {mission.stress_pct}%  (0/0 zones)")

    passages = retrieve("stress hydrique pomme de terre 0% seuils recommandations")
    prompt = build_prompt(mission, historique, passages)
    print("\n--- Prompt envoyé au LLM (extrait mission) ---")
    print(prompt.split("## Historique")[0])

    result = generate_diagnostic(prompt)
    print("\n--- Diagnostic généré ---")
    print(result.text)
    print(f"\n(latence : {result.latency_s:.1f}s)")


def cas_rag_hors_domaine() -> None:
    """Requête RAG explicitement hors du domaine couvert par le corpus
    (maladie fongique du blé — le corpus ne couvre que le stress
    hydrique de la pomme de terre) — teste si le LLM signale que le
    contexte ne couvre pas la question plutôt que d'improviser une
    réponse à partir de passages non pertinents."""
    print("\n" + "=" * 70)
    print("CAS LIMITE 2 — requête RAG hors du domaine du corpus")
    print("=" * 70)

    requete_hors_domaine = "traitement des maladies fongiques du blé, rouille jaune"
    passages = retrieve(requete_hors_domaine)

    print(f"Requête : {requete_hors_domaine!r}")
    print("Passages retournés par ChromaDB (top-k, pas de seuil de pertinence) :")
    for p in passages:
        print(f"  - [{p['source']}] distance={p['distance']:.3f}")
        print(f"    {p['text'][:100]}...")

    # On combine ces passages hors-sujet avec une vraie mission, pour voir
    # si le LLM les utilise à tort ou reconnaît qu'ils ne répondent pas
    # à la question posée sur le stress hydrique.
    mission = MissionReading(
        mission_id="M-EDGE-002",
        parcelle_id="PARC-EDGE-RAG",
        date=date(2026, 8, 21),
        culture="Pomme de terre",
        stress_ratio=0.45,
        zones_stressees=9,
        zones_totales=20,
        notes="",
    )
    init_db()
    insert_mission(mission)
    historique = get_historique("PARC-EDGE-RAG")
    prompt = build_prompt(mission, historique, passages)

    print("\n--- Contexte RAG injecté dans le prompt (hors-sujet, volontairement) ---")
    print(_format_rag_context(passages)[:300], "...")

    result = generate_diagnostic(prompt)
    print("\n--- Diagnostic généré (avec un contexte RAG hors-sujet) ---")
    print(result.text)
    print(f"\n(latence : {result.latency_s:.1f}s)")


if __name__ == "__main__":
    cas_donnee_incomplete()
    cas_rag_hors_domaine()
