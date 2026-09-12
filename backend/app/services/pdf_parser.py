"""
PDF -> per-page text extraction.

We use pdfplumber (not raw PyPDF2) specifically because it gives cleaner
text extraction for documents with tables/columns, and -- importantly for
citations -- it makes it trivial to keep track of WHICH page each piece of
text came from. Losing page numbers here would mean losing the ability to
cite "page 4" later, which is a core requirement.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

import pdfplumber

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PageText:
    page_number: int  # 1-indexed, human-friendly for citations
    text: str


class PDFParsingError(Exception):
    pass


def extract_pages(file_path: str | Path) -> List[PageText]:
    """
    Extract text from every page of a PDF, preserving page numbers.

    Returns a list of PageText, skipping pages that yield no extractable
    text (e.g. pure-image scanned pages) rather than failing the whole file.
    """
    file_path = Path(file_path)
    pages: List[PageText] = []

    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                text = text.strip()
                if text:
                    pages.append(PageText(page_number=i, text=text))
                else:
                    logger.warning(f"{file_path.name}: page {i} had no extractable text (scanned image?)")
    except Exception as exc:
        raise PDFParsingError(f"Failed to parse {file_path.name}: {exc}") from exc

    if not pages:
        raise PDFParsingError(
            f"{file_path.name}: no extractable text found in any page. "
            "This may be a scanned/image-only PDF (OCR not supported yet)."
        )

    logger.info(f"{file_path.name}: extracted text from {len(pages)} page(s)")
    return pages
