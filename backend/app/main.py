"""
FastAPI app entrypoint.

Run with:  uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import upload, chat, domains
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

app = FastAPI(
    title="Domain Q&A RAG Chatbot",
    description="Upload PDFs into subject 'domains' and ask questions answered via RAG.",
    version="1.0.0",
)

# Vite's default dev server port. Add your deployed frontend origin here too
# once you deploy (e.g. a Vercel URL).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(domains.router)


@app.get("/")
async def root():
    return {"status": "ok", "message": "RAG Q&A backend is running. See /docs for API."}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "llm_provider": settings.llm_provider,
        "embedding_model": settings.embedding_model,
    }


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting up. LLM provider = {settings.llm_provider}, top_k = {settings.top_k}")
    if settings.llm_provider == "claude" and not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY is not set -- /api/ask will fail until it is.")
