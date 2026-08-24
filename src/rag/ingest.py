"""Vectorisation du corpus agronomique dans ChromaDB (cahier des charges §4.2/§5).

Découpe chaque fichier Markdown du corpus en chunks (par section ##), les
transforme en embeddings via sentence-transformers, et les stocke dans une
base ChromaDB persistante locale — pas d'appel réseau après le premier
téléchargement du modèle d'embedding.

Usage: python -m src.rag.ingest
"""

import re

# Doit être importé avant sentence_transformers/chromadb : positionne
# HF_HUB_OFFLINE avant que huggingface_hub ne lise la variable d'env.
from src.config import CHROMA_COLLECTION, CHROMA_DIR, CORPUS_DIR, EMBEDDING_MODEL

import chromadb
from sentence_transformers import SentenceTransformer


def chunk_markdown(text: str, source: str) -> list[dict]:
    """Découpe un fichier Markdown en chunks par section de niveau ##.

    Chaque chunk garde le titre de section en tête pour donner du contexte
    à l'embedding et au LLM au moment de la récupération.
    """
    # On ignore le bloc de citation "placeholder" en tête de fichier pour
    # ne pas polluer les embeddings avec du méta-texte.
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

    # On repart d'une collection propre à chaque ingestion pour éviter les
    # doublons si le corpus a changé entre deux runs.
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
        print(f"Aucun fichier .md trouvé dans {CORPUS_DIR} (hors README.md).")
        return

    embeddings = model.encode([c["text"] for c in all_chunks]).tolist()
    collection.add(
        ids=[f"{c['source']}::{i}" for i, c in enumerate(all_chunks)],
        documents=[c["text"] for c in all_chunks],
        metadatas=[{"source": c["source"]} for c in all_chunks],
        embeddings=embeddings,
    )
    print(f"{len(all_chunks)} chunks indexés depuis {CORPUS_DIR} → {CHROMA_DIR}")


if __name__ == "__main__":
    build_index()
