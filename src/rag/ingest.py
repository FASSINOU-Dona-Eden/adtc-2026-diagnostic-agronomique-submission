"""Vectorization of the agronomic corpus into ChromaDB (specification §4.2/§5).

Splits each Markdown file of the corpus into chunks (by ## section), turns
them into embeddings via sentence-transformers, and stores them in a
local persistent ChromaDB store — no network call after the embedding
model's first download.

Usage: python -m src.rag.ingest
"""

import re

# Must be imported before sentence_transformers/chromadb: sets
# HF_HUB_OFFLINE before huggingface_hub reads the env var.
from src.config import CHROMA_COLLECTION, CHROMA_DIR, CORPUS_DIR, EMBEDDING_MODEL

import chromadb
from sentence_transformers import SentenceTransformer


def chunk_markdown(text: str, source: str) -> list[dict]:
    """Splits a Markdown file into chunks by level-## section.

    Each chunk keeps the section title at the top to give context
    to the embedding and to the LLM at retrieval time.
    """
    # Ignore the "placeholder" quote block at the top of the file so as
    # not to pollute the embeddings with meta-text.
    text = re.sub(r"^> ⚠️.*?\n\n", "", text, flags=re.DOTALL)

    sections = re.split(r"\n(?=## )", text)
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        chunks.append({"text": section, "source": source})
    return chunks


def build_index() -> None:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )

    # Start from a clean collection on every ingestion, to avoid
    # duplicates if the corpus changed between two runs.
    try:
        client.delete_collection(CHROMA_COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(CHROMA_COLLECTION)

    model = SentenceTransformer(EMBEDDING_MODEL)

    all_chunks: list[dict] = []
    for md_file in sorted(CORPUS_DIR.glob("*.md")):
        if md_file.name == "README.md":
            continue
        text = md_file.read_text(encoding="utf-8")
        all_chunks.extend(chunk_markdown(text, source=md_file.name))

    if not all_chunks:
        print(f"No .md file found in {CORPUS_DIR} (other than README.md).")
        return

    embeddings = model.encode([c["text"] for c in all_chunks]).tolist()
    collection.add(
        ids=[f"{c['source']}::{i}" for i, c in enumerate(all_chunks)],
        documents=[c["text"] for c in all_chunks],
        metadatas=[{"source": c["source"]} for c in all_chunks],
        embeddings=embeddings,
    )
    print(f"{len(all_chunks)} chunks indexed from {CORPUS_DIR} → {CHROMA_DIR}")


if __name__ == "__main__":
    build_index()
