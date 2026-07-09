"""
rag/vector_store.py — ChromaDB Vector Database
================================================
Manages the ChromaDB collection that stores embedded interview documents.

ChromaDB persists data to disk at CHROMA_PERSIST_DIR.
Each document stored with:
  - id        : unique string
  - embedding : vector from embedding model
  - document  : the combined text (question + answer)
  - metadata  : topic, type, difficulty, source
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional

from app.config import settings
from app.utils.logger import logger


class VectorStore:
    """ChromaDB wrapper with lazy initialisation."""

    def __init__(self):
        self._client     = None
        self._collection = None

    def _init(self):
        if self._collection is not None:
            return
        try:
            # PersistentClient saves data to disk automatically
            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir,
            )
            # get_or_create_collection: creates on first run, loads on subsequent
            self._collection = self._client.get_or_create_collection(
                name=settings.chroma_collection_name,
                # cosine distance is best for text similarity (normalised vectors)
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                f"ChromaDB collection '{settings.chroma_collection_name}' ready. "
                f"Documents: {self._collection.count()}"
            )
        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}")
            raise

    def count(self) -> int:
        """Return number of documents in the collection."""
        self._init()
        return self._collection.count()

    def add_documents(
        self,
        ids:        List[str],
        embeddings: List[List[float]],
        documents:  List[str],
        metadatas:  List[Dict],
    ) -> None:
        """
        Add documents to ChromaDB.
        If a document with the same id already exists, it is updated (upsert).
        """
        self._init()
        # upsert = insert or update — safe to call multiple times
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Upserted {len(ids)} documents into ChromaDB.")

    def query(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        where: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Find the most semantically similar documents to a query embedding.

        Args:
            query_embedding : vector of the query text
            n_results        : how many documents to return
            where            : optional metadata filter e.g. {"type": "technical"}

        Returns:
            List of dicts with keys: id, document, metadata, distance
        """
        self._init()

        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": min(n_results, self._collection.count() or 1),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        # Flatten ChromaDB's nested result structure
        documents = []
        for i in range(len(results["ids"][0])):
            documents.append({
                "id":       results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            })

        return documents

    def is_populated(self) -> bool:
        """Check if the vector store has documents."""
        try:
            return self.count() > 0
        except Exception:
            return False

    def reset(self) -> None:
        """Delete all documents (use for re-ingestion)."""
        self._init()
        self._client.delete_collection(settings.chroma_collection_name)
        self._collection = None
        self._init()
        logger.warning("ChromaDB collection reset.")


# Module-level singleton
vector_store = VectorStore()
