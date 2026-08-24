"""Recherche vectorielle dans le corpus agronomique indexé (§4.2).

Requête → embedding → top-k passages les plus proches, retournés comme
contexte texte prêt à insérer dans le prompt du LLM.
"""

# Doit être importé avant sentence_transformers/chromadb : positionne
# HF_HUB_OFFLINE avant que huggingface_hub ne lise la variable d'env.
from src.config import CHROMA_COLLECTION, CHROMA_DIR, EMBEDDING_MODEL, RAG_TOP_K

import chromadb
from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    # Chargé une seule fois par process : le modèle d'embedding a un coût
    # mémoire non négligeable, pas question de le recharger à chaque requête.
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def retrieve(query: str, top_k: int = RAG_TOP_K) -> list[dict]:
    """Retourne les top_k passages du corpus les plus pertinents pour la requête.

    Chaque résultat : {"text": ..., "source": ..., "distance": ...}
    """
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )
    try:
        collection = client.get_collection(CHROMA_COLLECTION)
    except Exception as exc:
        raise RuntimeError(
            "Index Chroma introuvable. Lancer d'abord : python -m src.rag.ingest"
        ) from exc

    embedding = _get_model().encode([query]).tolist()
    results = collection.query(query_embeddings=embedding, n_results=top_k)

    passages = []
    for text, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        passages.append({"text": text, "source": meta["source"], "distance": dist})
    return passages
