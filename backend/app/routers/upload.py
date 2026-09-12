"""Upload endpoint: PDF -> domain collection."""

import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.config import get_settings
from app.models.schemas import UploadResponse
from app.services.rag_pipeline import ingest_document
from app.services.pdf_parser import PDFParsingError
from app.utils.logger import get_logger

router = APIRouter(prefix="/api", tags=["upload"])
logger = get_logger(__name__)


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    domain: str = Form(..., description="Subject/domain name, e.g. 'DBMS' or 'Compiler-Design'"),
    file: UploadFile = File(...),
):
    settings = get_settings()

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported right now.")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest_path = upload_dir / file.filename

    # Stream to disk rather than reading fully into memory -- keeps memory
    # flat regardless of PDF size, and enforce a size cap while doing so.
    size = 0
    max_bytes = settings.max_upload_mb * 1024 * 1024
    try:
        with open(dest_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(413, f"File exceeds {settings.max_upload_mb}MB limit.")
                buffer.write(chunk)
    finally:
        await file.close()

    try:
        chunk_count = ingest_document(domain=domain, file_path=str(dest_path), filename=file.filename)
    except PDFParsingError as exc:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(422, str(exc))
    except Exception as exc:
        logger.error(f"Ingestion failed for {file.filename}: {exc}")
        dest_path.unlink(missing_ok=True)
        raise HTTPException(500, "Failed to process document. Check server logs.")

    return UploadResponse(
        domain=domain,
        filename=file.filename,
        chunks_created=chunk_count,
        message=f"'{file.filename}' indexed into domain '{domain}' ({chunk_count} chunks).",
    )
