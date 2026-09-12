# Domain Q&A Assistant

A Retrieval-Augmented Generation (RAG) chatbot for answering questions from your own PDFs — organized by subject ("domain") — with every answer citing the exact source file and page it came from.

Upload PDFs into a domain (e.g. `DBMS`, `Compiler-Design`), ask a question, and get an answer grounded strictly in that domain's documents, complete with numbered, clickable source citations.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [How the RAG Pipeline Works](#how-the-rag-pipeline-works)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Configuration Reference](#configuration-reference)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)

---

## Features

- 📂 **Domain-scoped knowledge bases** — each subject gets its own isolated vector collection, so subjects never cross-contaminate.
- 📄 **Drag-and-drop PDF ingestion** with automatic per-page text extraction.
- 🔍 **Semantic retrieval** via local sentence-transformer embeddings — no external embedding API required.
- 🧠 **LLM-generated answers** grounded in retrieved context, with automatic fallback between providers.
- 🔗 **Verifiable citations** — every claim in an answer links back to a specific source file and page number.
- 🚫 **Anti-hallucination guardrail** — the model is instructed to say "I don't know" rather than answer from general knowledge when the context is insufficient.

---

## Architecture

```
                         ┌───────────────────────────────┐
                         │      React (Vite) Frontend      │
                         │  • Drag/drop PDF upload          │
                         │  • Chat UI with citations         │
                         └────────────────┬─────────────────┘
                                          │ REST (axios)
                                          ▼
                         ┌───────────────────────────────┐
                         │        FastAPI Backend           │
                         │                                   │
  Upload flow:            │   POST /api/upload                │
  PDF → pdfplumber → chunker.py → embeddings.py →│──▶ ChromaDB
  (per page)      (RecursiveCharacterTextSplitter)  (MiniLM)  │   (per-domain
                                                                │   collection,
  Ask flow:                                                     │   persisted
  question → embed query → vector_store.query() ◀───────────────┘   to disk)
                    │
                    ▼
            Top-K chunks + metadata
                    │
                    ▼
            llm.py builds numbered RAG prompt
                    │
                    ▼
         Claude API (claude-sonnet-4-6)
         [falls back to Gemini if configured / on failure]
                    │
                    ▼
      Answer (cites [1][2]) + source chunks → POST /api/ask response
```

---

## How the RAG Pipeline Works

### 1. Ingestion — `POST /api/upload`

| Stage | Component | Responsibility |
|---|---|---|
| Extraction | `pdf_parser.py` | Extracts text **per page** via `pdfplumber`, tracking page numbers from the start so citations can later point to an exact page. |
| Chunking | `chunker.py` | Splits each page's text using LangChain's `RecursiveCharacterTextSplitter` (1000 chars, 150 overlap by default). The splitter prefers paragraph breaks, then sentences, then words, before falling back to a hard cut — preserving semantic units (a paragraph, a definition) more often than a naive fixed-size slice, and improving retrieval quality. Overlap prevents a boundary sentence from being orphaned. |
| Embedding | `embeddings.py` | Converts each chunk into a 384-dimensional vector using `all-MiniLM-L6-v2` via `sentence-transformers` — local, free, no API key, and fast enough on CPU for a college-scale document set. |
| Storage | `vector_store.py` | Persists vectors, text, and metadata (source file, page number, chunk index) to a **ChromaDB collection dedicated to that domain**. |

### 2. Retrieval + Generation — `POST /api/ask`

1. The question is embedded using the **same model** used for documents, ensuring query and document embeddings share a vector space.
2. ChromaDB returns the `top_k` most similar chunks (cosine similarity) from the selected domain's collection only.
3. `llm.py` constructs a prompt presenting each chunk as a **numbered excerpt** with its source and page, instructing the model to answer *only* from that context and cite excerpt numbers (e.g., `[1]`). This is the core anti-hallucination guardrail.
4. The backend maps each citation marker back to its real `source_file` and `page_number`, returning them alongside the answer so the frontend can render expandable source citations.
5. `LLM_PROVIDER` in `.env` selects Claude or Gemini as the primary provider; if the primary call fails and a secondary key is configured, one automatic fallback attempt is made.

---

## Tech Stack

**Backend:** FastAPI · pydantic-settings · pdfplumber · LangChain (text splitting) · sentence-transformers · ChromaDB · Anthropic / Gemini APIs

**Frontend:** React (Vite) · Axios

---

## Project Structure

```
rag-qa-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, router wiring
│   │   ├── config.py            # .env-driven settings (pydantic-settings)
│   │   ├── models/schemas.py    # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── pdf_parser.py    # PDF -> per-page text
│   │   │   ├── chunker.py       # page text -> overlapping chunks
│   │   │   ├── embeddings.py    # sentence-transformers wrapper
│   │   │   ├── vector_store.py  # ChromaDB, per-domain collections
│   │   │   ├── llm.py           # Claude/Gemini + RAG prompt building
│   │   │   └── rag_pipeline.py  # orchestrates the two flows above
│   │   ├── routers/
│   │   │   ├── upload.py        # POST /api/upload
│   │   │   ├── chat.py          # POST /api/ask
│   │   │   └── domains.py       # GET  /api/domains
│   │   └── utils/logger.py
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.jsx               # layout: sidebar + chat
    │   ├── components/
    │   │   ├── DomainPanel.jsx   # subject list + drag-drop upload
    │   │   ├── ChatWindow.jsx    # message history + input
    │   │   ├── MessageBubble.jsx
    │   │   └── SourceCitation.jsx
    │   └── services/api.js       # axios calls to the backend
    ├── package.json
    └── .env.example
```

---

## Getting Started

> **Windows note:** Set up this project **outside any OneDrive-synced folder** (e.g. `C:\dev\...`, not `C:\Users\<you>\OneDrive\...`). OneDrive's live sync can corrupt `node_modules` mid-install.

### Prerequisites

- Python 3.10+
- Node.js 18+
- An Anthropic API key (and/or a Gemini API key for fallback)

### 1. Clone / Place the Project

```powershell
mkdir C:\dev
cd C:\dev
# copy or extract the rag-qa-chatbot folder here
cd C:\dev\rag-qa-chatbot
```

### 2. Backend Setup

```powershell
cd C:\dev\rag-qa-chatbot\backend

# Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# If PowerShell blocks the activation script, run once (as your user, not admin):
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

pip install -r requirements.txt

# Configure API keys
copy .env.example .env
notepad .env    # paste your ANTHROPIC_API_KEY

# Start the server (first request downloads the MiniLM model, ~80MB)
uvicorn app.main:app --reload --port 8000
```

Interactive API docs: **http://localhost:8000/docs**

### 3. Frontend Setup

Open a **second** terminal (leave the backend running):

```powershell
cd C:\dev\rag-qa-chatbot\frontend

npm install
copy .env.example .env    # only needed if backend runs on a non-default URL

npm run dev
```

App: **http://localhost:5173**

### 4. Try It Out

1. In the sidebar, enter a subject name (e.g. `DBMS`) and drop in a PDF.
2. Wait for the "indexed" confirmation.
3. Ask a question in the chat — the answer will cite `[1]`, `[2]`, etc., with expandable source excerpts and page numbers underneath.

---

## Configuration Reference

`backend/.env`

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `claude` | `claude` or `gemini` |
| `ANTHROPIC_API_KEY` | — | Required if provider is `claude` |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Claude model ID |
| `GEMINI_API_KEY` | — | Optional fallback provider |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Local sentence-transformers model |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `150` | Chunking parameters |
| `TOP_K` | `4` | Chunks retrieved per question |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | ChromaDB storage path |
| `MAX_UPLOAD_MB` | `25` | Upload size cap |

---

## Known Limitations

- **Scanned/image-only PDFs are not supported** — `pdfplumber` requires a text layer; OCR (e.g. `pytesseract`) would be the natural next step.
- **Pure vector similarity retrieval** — no re-ranking or hybrid BM25 + vector search yet. Sufficient for a college-scale corpus, but a larger corpus would benefit from a re-ranker.
- **No conversation memory** — each question is answered independently of prior chat turns.

## Roadmap

- [ ] OCR support for scanned PDFs
- [ ] Hybrid BM25 + vector retrieval with re-ranking
- [ ] Condensed chat history in the RAG prompt to support follow-up questions (e.g., "what about the second one?")

---

## License

Specify a license (e.g., MIT) here.
