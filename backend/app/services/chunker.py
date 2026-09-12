"""
Chunking: split extracted page text into overlapping chunks for embedding.

Why RecursiveCharacterTextSplitter specifically (interview-relevant point):
It tries to split on paragraph breaks first, then sentences, then words --
only falling back to a hard character cut as a last resort. This keeps
semantic units (a paragraph, a definition) intact far more often than a
naive fixed-size slice would, which directly improves retrieval quality
because embeddings of a "whole thought" are more meaningful than embeddings
of an arbitrary text fragment.

Overlap (chunk_overlap) exists so that a sentence sitting right at a chunk
boundary isn't orphaned -- it appears in full in at least one chunk.
"""

from dataclasses import dataclass
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.pdf_parser import PageText
from app.config import get_settings


@dataclass
class Chunk:
    text: str
    page_number: int
    chunk_index: int  # position within the document, for stable citation ids


def chunk_pages(pages: List[PageText]) -> List[Chunk]:
    """
    Chunk each page's text independently (so a chunk never silently spans
    two pages, which would make page-number citation ambiguous), then
    assign a running chunk_index across the whole document.
    """
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: List[Chunk] = []
    running_index = 0
    for page in pages:
        page_chunks = splitter.split_text(page.text)
        for text in page_chunks:
            chunks.append(
                Chunk(text=text, page_number=page.page_number, chunk_index=running_index)
            )
            running_index += 1

    return chunks
