"""Configuration centrale du pipeline ADTC 2026.

Toutes les valeurs modifiables (modèle, chemins, seuils) vivent ici pour
éviter les constantes éparpillées dans le code.
"""

import os
from pathlib import Path

# --- Mode hors-ligne strict ---
# Par défaut, huggingface_hub/sentence-transformers contacte le réseau à
# chaque chargement de modèle pour vérifier des métadonnées, MÊME si le
# modèle est déjà en cache local (~88 Mo mesurés en trafic réel lors d'un
# test avec réseau dispo, pour un modèle pourtant déjà téléchargé).
# Contraire à la contrainte "100% hors-ligne" du concours (cahier des
# charges §1). On force l'usage du cache local uniquement — si le modèle
# n'y est pas encore, ça échoue explicitement plutôt que d'appeler le
# réseau en silence. Doit être positionné AVANT tout import de
# sentence_transformers / huggingface_hub.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
# ChromaDB envoie de la télémétrie anonymisée par défaut (posthog) — autre
# fuite réseau silencieuse, même config-only, à couper explicitement.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# --- Chemins ---
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CORPUS_DIR = ROOT_DIR / "corpus"
DB_PATH = DATA_DIR / "missions.db"
CHROMA_DIR = DATA_DIR / "chroma"

# --- Modèle LLM (Ollama) ---
# Décision actée le 21/08 après comparaison RAM/latence/fiabilité : gemma3:1b
# hallucine des chiffres absents du contexte fourni (3/3 tests), inacceptable
# pour un diagnostic. On garde gemma3:4b malgré son coût RAM plus élevé.
OLLAMA_MODEL = "gemma3:4b"
# Surchargeable via env (utile pour pointer un serveur Ollama de test isolé,
# ex: profiling en CPU pur — voir scripts/profile_cpu_only.sh).
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# --- RAG ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # léger, tourne bien en CPU/8 Go
CHROMA_COLLECTION = "corpus_agronomique"
RAG_TOP_K = 3

# --- Seuils métier ---
# Grille de niveaux — doit rester synchronisée avec la table de
# corpus/seuils_alerte.md (à ajuster ensemble si Piste B change les seuils).
#
# Calculée en code plutôt que laissée à la charge du LLM : un test sur 4
# scénarios (22/08) a montré gemma3:4b se tromper de palier en dérivant
# lui-même la classification depuis le tableau récupéré par le RAG (ex:
# 75% classé "alerte" au lieu de "critique"). Conforme à la règle du
# cahier des charges §4.3 : le LLM interprète, il ne calcule pas — la
# classification est un calcul, donc elle ne lui revient pas.
def classify_niveau(stress_ratio: float, zones_totales: int | None = None) -> str:
    """Classe un ratio de stress (0.0-1.0) selon la grille de seuils du corpus.

    zones_totales=0 signifie qu'aucune zone n'a pu être mesurée (ex: panne
    capteur, scan interrompu) — à distinguer de "0% de stress mesuré sur des
    zones valides", qui est un vrai résultat "Normal". Cas découvert et
    documenté via scripts/test_edge_cases.py : sans cette distinction, une
    panne capteur était classée "Normal" — un faux négatif potentiel côté
    opérateur (situation perçue comme saine alors qu'aucune mesure fiable
    n'existe). Les 4 paliers existants (Normal/Vigilance/Alerte/Critique)
    sont inchangés pour tout zones_totales != 0.
    """
    if zones_totales == 0:
        return "Données insuffisantes"
    if stress_ratio <= 0.15:
        return "Normal"
    if stress_ratio <= 0.35:
        return "Vigilance"
    if stress_ratio <= 0.60:
        return "Alerte"
    return "Critique"
