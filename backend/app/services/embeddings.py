"""
Local embedding model wrapper.

all-MiniLM-L6-v2 is chosen deliberately over an API-based embedding model:
- Free and runs on CPU (~80MB model, <100ms per chunk on a laptop).
- 384-dim vectors keep ChromaDB fast and lightweight for a college-scale
  corpus (hundreds to low-thousands of chunks).
- No API key/network dependency for the embedding step means uploads work
  even if your LLM provider's API is briefly down -- only the /ask step
  needs external network access.

The model is loaded once (module-level singleton) since loading it per
request would add several seconds of latency to every call.
"""

from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache
def _get_model() -> SentenceTransformer:
    settings = get_settings()
    logger.info(f"Loading embedding model '{settings.embedding_model}' (first call only)...")
    return SentenceTransformer(settings.embedding_model)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a batch of texts. Batching is much faster than one-by-one calls."""
    model = _get_model()
    vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return vectors.tolist()


def embed_query(query: str) -> List[float]:
    """Embed a single user question."""
    return embed_texts([query])[0]
