"""
rag/embeddings.py — Text Embedding Model
=========================================
Converts text into dense vectors for semantic search.

Primary  : IBM Granite Embedding (ibm/slate-125m-english-rtrvr via watsonx.ai)
Fallback : sentence-transformers/all-MiniLM-L6-v2 (local, free, fast)

The fallback activates automatically if IBM credentials are missing.
Migration to IBM embeddings: just fill WATSONX_API_KEY in .env — no code change.
"""

from typing import List
from app.config import settings
from app.utils.logger import logger


class EmbeddingModel:
    """Lazy-loaded embedding model with IBM Granite primary + local fallback."""

    def __init__(self):
        self._model = None
        self._mode  = None   # "ibm" or "local"

    def _load(self):
        if self._model is not None:
            return

        # Try IBM Granite Embedding first
        if (settings.watsonx_api_key and
                settings.watsonx_api_key != "your-ibm-cloud-api-key-here"):
            try:
                from ibm_watsonx_ai import Credentials
                from ibm_watsonx_ai.foundation_models import Embeddings
                from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams

                creds = Credentials(
                    url=settings.watsonx_url,
                    api_key=settings.watsonx_api_key,
                )
                self._model = Embeddings(
                    model_id=settings.granite_embed_model_id,
                    credentials=creds,
                    project_id=settings.watsonx_project_id,
                    params={EmbedParams.TRUNCATE_INPUT_TOKENS: 512},
                )
                self._mode = "ibm"
                logger.info(f"IBM Granite Embedding loaded: {settings.granite_embed_model_id}")
                return
            except Exception as e:
                logger.warning(f"IBM embedding failed ({e}), falling back to local model.")

        # Fallback: sentence-transformers (runs locally, no API needed)
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self._mode  = "local"
            logger.info("Local embedding model loaded: all-MiniLM-L6-v2")
        except Exception as e:
            raise RuntimeError(f"Could not load any embedding model: {e}")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Convert a list of strings to a list of embedding vectors."""
        self._load()

        if self._mode == "ibm":
            # IBM SDK returns EmbeddingsResults — extract vectors
            result = self._model.embed_documents(texts)
            return result
        else:
            # sentence-transformers returns numpy arrays → convert to list
            vecs = self._model.encode(texts, show_progress_bar=False)
            return [v.tolist() for v in vecs]

    def embed_one(self, text: str) -> List[float]:
        """Embed a single string."""
        return self.embed([text])[0]

    @property
    def mode(self) -> str:
        self._load()
        return self._mode


# Module-level singleton
embedding_model = EmbeddingModel()
