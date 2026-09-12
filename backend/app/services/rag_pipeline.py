"""
Top-level orchestration for the two core flows:

  ingest_document(): PDF -> pages -> chunks -> embeddings -> ChromaDB
  answer_question(): question -> embed -> retrieve top-k -> prompt -> LLM -> answer+sources

Keeping this as a thin orchestration layer (no business logic of its own)
means each step is independently testable/swappable -- e.g. you could
replace pdf_parser with a .docx parser later without touching this file.
"""

from pathlib import Path
from typing import List

from app.config import get_settings
from app.models.schemas import SourceChunk
from app.services import pdf_parser, chunker, vector_store, llm
from app.utils.logger import get_logger

logger = get_logger(__name__)


def ingest_document(domain: str, file_path: str, filename: str) -> int:
    """Full ingestion pipeline for one uploaded PDF. Returns chunk count."""
    pages = pdf_parser.extract_pages(file_path)
    chunks = chunker.chunk_pages(pages)
    stored = vector_store.add_chunks(domain=domain, source_file=filename, chunks=chunks)
    return stored


def _distance_to_similarity(distance: float) -> float:
    """
    Chroma's default space is squared L2 / cosine distance depending on
    config; for our normalized MiniLM embeddings, cosine distance in
    [0, 2] maps cleanly to similarity = 1 - distance/2. We clamp to keep
    the score in a friendly [0, 1] range even if a value falls outside.
    """
    similarity = 1 - (distance / 2)
    return max(0.0, min(1.0, similarity))


def answer_question(domain: str, question: str, top_k: int | None = None) -> tuple[str, List[SourceChunk]]:
    """Full retrieval + generation pipeline for one question."""
    settings = get_settings()
    k = top_k or settings.top_k

    raw = vector_store.query(domain=domain, question=question, top_k=k)

    documents = raw.get("documents", [[]])[0]
    metadatas = raw.get("metadatas", [[]])[0]
    distances = raw.get("distances", [[]])[0]

    if not documents:
        return (
            "No documents have been uploaded to this domain yet, so I have no context to answer from.",
            [],
        )

    sources = [
        SourceChunk(
            content=doc,
            source_file=meta.get("source_file", "unknown"),
            page_number=meta.get("page_number"),
            chunk_index=meta.get("chunk_index", i),
            similarity_score=round(_distance_to_similarity(dist), 4),
        )
        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances))
    ]

    answer = llm.generate_answer(question, sources)
    return answer, sources
