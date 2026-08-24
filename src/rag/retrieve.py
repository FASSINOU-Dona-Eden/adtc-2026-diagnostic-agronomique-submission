"""Vector search in the indexed agronomic corpus (§4.2).

Query → embedding → top-k closest passages, returned as
text context ready to insert into the LLM prompt.
"""

# Must be imported before sentence_transformers/chromadb: sets
# HF_HUB_OFFLINE before huggingface_hub reads the env var.
from src.config import CHROMA_COLLECTION, CHROMA_DIR, EMBEDDING_MODEL, RAG_TOP_K

import chromadb
from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    # Loaded once per process: the embedding model has a non-negligible
    # memory cost, no question of reloading it on every request.
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def retrieve(query: str, top_k: int = RAG_TOP_K) -> list[dict]:
    """Returns the top_k corpus passages most relevant to the query.

    Each result: {"text": ..., "source": ..., "distance": ...}
    """
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )
    try:
        collection = client.get_collection(CHROMA_COLLECTION)
    except Exception as exc:
        raise RuntimeError(
            "Chroma index not found. Run first: python -m src.rag.ingest"
        ) from exc

    embedding = _get_model().encode([query]).tolist()
    results = collection.query(query_embeddings=embedding, n_results=top_k)

    passages = []
    for text, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        passages.append({"text": text, "source": meta["source"], "distance": dist})
    return passages
