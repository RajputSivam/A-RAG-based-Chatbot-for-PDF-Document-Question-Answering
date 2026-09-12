"""Ask endpoint: question -> retrieval -> LLM answer + cited sources."""

from fastapi import APIRouter, HTTPException

from app.models.schemas import AskRequest, AskResponse
from app.services.rag_pipeline import answer_question
from app.utils.logger import get_logger

router = APIRouter(prefix="/api", tags=["chat"])
logger = get_logger(__name__)


@router.post("/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest):
    try:
        answer, sources = answer_question(
            domain=payload.domain, question=payload.question, top_k=payload.top_k
        )
    except ValueError as exc:
        # Raised by vector_store.query when the domain doesn't exist yet.
        raise HTTPException(404, str(exc))
    except Exception as exc:
        logger.error(f"Failed to answer question in domain '{payload.domain}': {exc}")
        raise HTTPException(500, "Failed to generate an answer. Check server logs.")

    return AskResponse(
        answer=answer,
        sources=sources,
        domain=payload.domain,
        question=payload.question,
    )
