"""
LLM call layer: builds the RAG prompt and calls Claude (default) or Gemini.

Design notes (useful talking points for an interview):
- The prompt explicitly numbers each retrieved chunk ([1], [2], ...) and
  instructs the model to cite by number. This is what makes "answer +
  citations" reliable -- we're not asking the model to invent page numbers
  from memory, we're asking it to reference the numbered context we already
  control, and we map [1]/[2]/etc. back to real source_file/page_number
  ourselves in the response.
- The prompt tells the model to say "I don't have enough information" if
  the retrieved chunks don't answer the question, instead of hallucinating
  from its own general knowledge. This is the core anti-hallucination
  guardrail of the whole RAG system.
- Provider is chosen via config (llm_provider), so swapping Claude<->Gemini
  is a .env change, not a code change.
"""

from typing import List

import anthropic

from app.config import get_settings
from app.models.schemas import SourceChunk
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a precise Q&A assistant that answers questions ONLY using the \
numbered context excerpts provided below. Follow these rules strictly:

1. Base your answer only on the provided context. Do not use outside knowledge.
2. If the context does not contain enough information to answer, say so plainly \
   instead of guessing.
3. When you use information from an excerpt, cite it inline using its number, \
   e.g. "...as shown in [1]." Use multiple citations if multiple excerpts support a point.
4. Be concise and direct. Do not repeat the question back.
"""


def _build_context_block(chunks: List[SourceChunk]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        page_info = f", page {chunk.page_number}" if chunk.page_number else ""
        parts.append(f"[{i}] (source: {chunk.source_file}{page_info})\n{chunk.content}")
    return "\n\n".join(parts)


def build_user_message(question: str, chunks: List[SourceChunk]) -> str:
    context_block = _build_context_block(chunks)
    return (
        f"Context excerpts:\n\n{context_block}\n\n"
        f"---\n\nQuestion: {question}\n\n"
        "Answer using only the context above, citing excerpt numbers like [1]."
    )


def _call_claude(user_message: str) -> str:
    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def _call_gemini(user_message: str) -> str:
    # Imported lazily so the `google-generativeai` package is only required
    # if the user actually configures the Gemini fallback.
    import google.generativeai as genai

    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=SYSTEM_PROMPT,
    )
    response = model.generate_content(user_message)
    return response.text


def generate_answer(question: str, chunks: List[SourceChunk]) -> str:
    settings = get_settings()
    user_message = build_user_message(question, chunks)

    provider = settings.llm_provider.lower()
    try:
        if provider == "gemini":
            return _call_gemini(user_message)
        return _call_claude(user_message)
    except Exception as exc:
        logger.error(f"Primary provider '{provider}' failed: {exc}")
        # Simple one-shot fallback: if Claude fails and a Gemini key is
        # configured, try Gemini before giving up (and vice versa).
        try:
            if provider == "claude" and settings.gemini_api_key:
                logger.info("Falling back to Gemini...")
                return _call_gemini(user_message)
            if provider == "gemini" and settings.anthropic_api_key:
                logger.info("Falling back to Claude...")
                return _call_claude(user_message)
        except Exception as fallback_exc:
            logger.error(f"Fallback provider also failed: {fallback_exc}")
        raise
