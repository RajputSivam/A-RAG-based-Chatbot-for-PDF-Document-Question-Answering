"""
ChromaDB wrapper providing one collection per "domain"/subject.

Why one Chroma *collection* per domain instead of one big collection with a
"domain" metadata filter?
- Simpler mental model: a domain IS a collection, so "list domains" is just
  "list collections" -- no risk of a query accidentally leaking across
  domains if a filter is forgotten somewhere.
- Chroma collections are cheap; this scales fine for a handful to dozens
  of subjects (a college use case, not a multi-tenant SaaS with thousands).

We bring our own embeddings (from embeddings.py) rather than letting Chroma
call an embedding function internally -- this keeps the embedding model a
single, explicit, swappable piece of the pipeline (again: interview-friendly,
and means you're not locked into whatever default Chroma ships with).
"""

from typing import List, Optional
import uuid

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings
from app.services.embeddings import embed_texts, embed_query
from app.services.chunker import Chunk
from app.utils.logger import get_logger

logger = get_logger(__name__)

_client: Optional[chromadb.ClientAPI] = None


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def _collection_name(domain: str) -> str:
    # Chroma collection names have character restrictions; keep it simple
    # and predictable by lowercasing + replacing spaces.
    return f"domain_{domain.strip().lower().replace(' ', '_')}"


def add_chunks(domain: str, source_file: str, chunks: List[Chunk]) -> int:
    """Embed and store chunks from one document into a domain's collection."""
    if not chunks:
        return 0

    client = get_client()
    collection = client.get_or_create_collection(name=_collection_name(domain))

    texts = [c.text for c in chunks]
    vectors = embed_texts(texts)
    ids = [f"{source_file}_{c.chunk_index}_{uuid.uuid4().hex[:8]}" for c in chunks]
    metadatas = [
        {"source_file": source_file, "page_number": c.page_number, "chunk_index": c.chunk_index}
        for c in chunks
    ]

    collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas)
    logger.info(f"Stored {len(chunks)} chunks from '{source_file}' into domain '{domain}'")
    return len(chunks)


def query(domain: str, question: str, top_k: int) -> dict:
    """
    Retrieve the top_k most similar chunks to `question` from a domain.

    Returns Chroma's raw query result shape:
    {"documents": [[...]], "metadatas": [[...]], "distances": [[...]]}
    """
    client = get_client()
    try:
        collection = client.get_collection(name=_collection_name(domain))
    except Exception as exc:
        raise ValueError(f"Domain '{domain}' does not exist or has no documents yet.") from exc

    query_vector = embed_query(question)
    return collection.query(query_embeddings=[query_vector], n_results=top_k)


def list_domains() -> List[dict]:
    client = get_client()
    result = []
    for coll in client.list_collections():
        # Strip our "domain_" prefix back to a friendly display name.
        friendly = coll.name.removeprefix("domain_")
        count = coll.count()
        result.append({"name": friendly, "chunk_count": count})
    return result
