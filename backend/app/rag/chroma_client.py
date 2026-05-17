"""ChromaDB client for RAG — analysis embeddings + semantic search."""
import logging
from typing import Optional

import chromadb
from chromadb.config import Settings

from app.config import settings

logger = logging.getLogger(__name__)

_chroma_client: Optional[chromadb.Client] = None
_analysis_collection = None
_news_collection = None


def get_chroma_client() -> chromadb.Client:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
    return _chroma_client


def get_analysis_collection():
    global _analysis_collection
    if _analysis_collection is None:
        client = get_chroma_client()
        _analysis_collection = client.get_or_create_collection(
            name="stock_analyses",
            metadata={"hnsw:space": "cosine"},
        )
    return _analysis_collection


def get_news_collection():
    global _news_collection
    if _news_collection is None:
        client = get_chroma_client()
        _news_collection = client.get_or_create_collection(
            name="financial_news",
            metadata={"hnsw:space": "cosine"},
        )
    return _news_collection


def embed_analysis(analysis_id: str, symbol: str, text_summary: str, metadata: dict = None):
    """Embed an analysis summary into ChromaDB."""
    from app.rag.embeddings import embed_text
    try:
        embedding = embed_text(text_summary)
        collection = get_analysis_collection()
        collection.upsert(
            ids=[analysis_id],
            embeddings=[embedding],
            documents=[text_summary],
            metadatas=[{"symbol": symbol, **(metadata or {})}],
        )
        logger.info(f"Embedded analysis {analysis_id} for {symbol}")
    except Exception as e:
        logger.error(f"Failed to embed analysis {analysis_id}: {e}")


def search_similar_analyses(query: str, symbol: Optional[str] = None, n_results: int = 5) -> list:
    """Semantic search over past analyses."""
    from app.rag.embeddings import embed_text
    try:
        embedding = embed_text(query)
        collection = get_analysis_collection()
        where = {"symbol": symbol} if symbol else None
        results = collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            where=where,
        )
        return [
            {"id": id_, "document": doc, "metadata": meta, "distance": dist}
            for id_, doc, meta, dist in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]
    except Exception as e:
        logger.error(f"ChromaDB search failed: {e}")
        return []
