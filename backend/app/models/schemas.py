"""
Pydantic models for request/response validation.

Keeping these separate from business logic means FastAPI auto-generates
accurate OpenAPI docs (visible at /docs) and you get free 422 validation
errors instead of hand-rolled checks.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    domain: str
    filename: str
    chunks_created: int
    message: str


class DomainInfo(BaseModel):
    name: str
    document_count: int
    chunk_count: int


class SourceChunk(BaseModel):
    """One retrieved chunk, returned alongside the answer for citation."""
    content: str
    source_file: str
    page_number: Optional[int] = None
    chunk_index: int
    similarity_score: float = Field(..., description="Higher = more relevant (0-1, cosine)")


class AskRequest(BaseModel):
    domain: str = Field(..., description="Which collection/subject to search within")
    question: str = Field(..., min_length=1)
    top_k: Optional[int] = Field(None, description="Override default retrieval depth")


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]
    domain: str
    question: str
