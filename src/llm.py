"""Local LLM call via Ollama (§4.3).

The model only interprets/rephrases: it receives data that is already
computed (stress ratio, history, RAG passages) and writes a diagnosis
in natural language. It never sees an image, computes nothing itself.
"""

import time
from dataclasses import dataclass

import ollama

from src.config import OLLAMA_HOST, OLLAMA_MODEL

SYSTEM_PROMPT = """\
You are an agronomic assistant helping a field operator interpret \
the results of a drone mission over a plot of land.

Strict rules:
- You NEVER receive an image. You work solely from the figures \
and the context provided in the message.
- You never invent a figure: you rephrase and interpret the ones you are given.
- Your diagnosis must be clear, concise (5-8 sentences), in English, and \
end with a concrete, actionable recommendation.
- If the provided context (history, technical sheets) does not cover a point, \
say so rather than inventing it.
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
        # keep_alive=0: unloads the model from RAM immediately after this
        # response, instead of keeping it loaded for 5 min by default.
        # Without this, Ollama's internal context cache grows with every
        # successive call within the same server session (measured: ~3.65
        # GiB in isolation → ~4.3-4.4 GiB after 3-4 calls in a row), which
        # caused an OOM confirmed by the kernel while pre-generating the
        # demo diagnoses (08/24). keep_alive=0 makes every call
        # structurally bounded at ~3.65 GiB, regardless of how many
        # generations are chained — at the cost of reloading the model
        # (~10-15s) on every call, already absorbed into the measured
        # latency. See the specification document, Block 5 / risks.
        keep_alive=0,
    )
    latency = time.perf_counter() - start
    return GenerationResult(text=response["message"]["content"], latency_s=latency)
