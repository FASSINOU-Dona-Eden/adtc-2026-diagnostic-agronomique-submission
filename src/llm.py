"""Appel du LLM local via Ollama (§4.3).

Le modèle ne fait qu'interpréter/reformuler : il reçoit des données déjà
calculées (stress ratio, historique, passages RAG) et rédige un diagnostic
en langage naturel. Il ne voit jamais d'image, ne calcule rien lui-même.
"""

import time
from dataclasses import dataclass

import ollama

from src.config import OLLAMA_HOST, OLLAMA_MODEL

SYSTEM_PROMPT = """\
Tu es un assistant agronomique qui aide un opérateur terrain à interpréter \
les résultats d'une mission drone sur une parcelle.

Règles strictes :
- Tu ne reçois JAMAIS d'image. Tu travailles uniquement à partir des chiffres \
et du contexte fournis dans le message.
- Tu n'inventes aucun chiffre : tu reformules et interprètes ceux qu'on te donne.
- Ton diagnostic doit être clair, concis (5-8 phrases), en français, et se \
terminer par une recommandation actionnable concrète.
- Si le contexte fourni (historique, fiches techniques) ne couvre pas un point, \
dis-le plutôt que d'inventer.
"""


@dataclass
class GenerationResult:
    text: str
    latency_s: float


def generate_diagnostic(prompt: str, model: str = OLLAMA_MODEL) -> GenerationResult:
    client = ollama.Client(host=OLLAMA_HOST)
    start = time.perf_counter()
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        # keep_alive=0 : décharge le modèle de la RAM immédiatement après
        # cette réponse, au lieu de le garder chargé 5 min par défaut. Sans
        # ça, le cache de contexte interne d'Ollama grossit à chaque appel
        # successif dans la même session serveur (mesuré : ~3,65 Gio en
        # isolation → ~4,3-4,4 Gio après 3-4 appels d'affilée), ce qui a
        # provoqué un OOM confirmé par le noyau lors de la pré-génération
        # des diagnostics de démo (24/08). keep_alive=0 rend chaque appel
        # structurellement borné à ~3,65 Gio, quel que soit le nombre de
        # générations enchaînées — au prix d'un rechargement du modèle
        # (~10-15s) à chaque appel, déjà absorbé dans la latence mesurée.
        # Voir cahier des charges, Bloc 5 / risques.
        keep_alive=0,
    )
    latency = time.perf_counter() - start
    return GenerationResult(text=response["message"]["content"], latency_s=latency)
