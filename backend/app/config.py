"""
Centralized configuration for the RAG backend.

Why pydantic-settings instead of plain os.getenv() calls scattered around?
- Single source of truth for every tunable (chunk size, top-k, model names).
- Type validation happens once, at startup, instead of failing deep inside
  a request handler with a confusing TypeError.
- Interview-friendly: you can point at ONE file and explain every knob
  in your RAG pipeline.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---- LLM provider selection -------------------------------------------------
    # "claude" (default) or "gemini". Lets you swap providers via .env with zero
    # code changes -- useful if you hit rate limits on one provider mid-demo.
    llm_provider: str = "claude"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # ---- Embeddings ---------------------------------------------------------------
    # Local, free, no API key. Runs on CPU fine for a college-scale document set.
    embedding_model: str = "all-MiniLM-L6-v2"

    # ---- Chunking -------------------------------------------------------------
    # 1000/150 is a common starting point for prose-heavy docs (notes, textbooks):
    # large enough to keep a paragraph's context intact, with enough overlap that
    # a sentence split across chunk boundaries still appears whole in at least one
    # chunk.
    chunk_size: int = 1000
    chunk_overlap: int = 150

    # ---- Retrieval ------------------------------------------------------------
    top_k: int = 4

    # ---- Storage paths --------------------------------------------------------
    chroma_persist_dir: str = "./data/chroma"
    upload_dir: str = "./uploads"

    # ---- Misc -------------------------------------------------------------
    max_upload_mb: int = 25
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Cached so we parse .env once, not on every request."""
    return Settings()
