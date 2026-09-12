# Domain Q&A Assistant — RAG Chatbot

Upload PDFs into subject "domains" (e.g. `DBMS`, `Compiler-Design`) and ask
questions answered via Retrieval-Augmented Generation, with every answer
citing the exact source file and page it came from.

## Architecture

```
                         ┌─────────────────────────────┐
                         │   React (Vite) Frontend      │
                         │  - Drag/drop PDF upload      │
                         │  - Chat UI + citations       │
                         └───────────────┬─────────────┘
                                         │ REST (axios)
                                         ▼
                         ┌─────────────────────────────┐
                         │   FastAPI Backend             │
                         │                               │
  Upload flow:            │  POST /api/upload             │
  PDF ──▶ pdfplumber ──▶ chunker.py ──▶ embeddings.py ──▶│──▶ ChromaDB
  (per page)   (RecursiveCharacterTextSplitter) (MiniLM)  │   (per-domain
                                                            │   collection,
  Ask flow:                                                 │   persisted
  question ──▶ embed query ──▶ vector_store.query() ◀──────┘   to disk)
                    │
                    ▼
            top-k chunks + metadata
                    │
                    ▼
            llm.py builds numbered RAG prompt
                    │
                    ▼
         Claude API (claude-sonnet-4-6)
         [falls back to Gemini if configured / on failure]
                    │
                    ▼
      answer (cites [1][2]) + source chunks ──▶ POST /api/ask response
```

## How the RAG pipeline works

**1. Ingestion (`POST /api/upload`)**
- `pdf_parser.py` extracts text **per page** using `pdfplumber` — page numbers
  are tracked from the start so citations can point to an exact page later.
- `chunker.py` splits each page's text with LangChain's
  `RecursiveCharacterTextSplitter` (1000 chars, 150 overlap by default). This
  splitter tries paragraph breaks, then sentences, then words before falling
  back to a hard cut — keeping semantic units (a paragraph, a definition)
  intact more often than a naive fixed-size slice, which improves retrieval
  quality. Overlap ensures a sentence at a chunk boundary isn't orphaned.
- `embeddings.py` turns each chunk into a 384-dim vector using
  `all-MiniLM-L6-v2` (via `sentence-transformers`) — local, free, no API key,
  fast enough on CPU for a college-scale document set.
- `vector_store.py` stores the vectors + text + metadata (source file, page
  number, chunk index) in a **ChromaDB collection dedicated to that domain**,
  so subjects never cross-contaminate.

**2. Retrieval + Generation (`POST /api/ask`)**
- The question is embedded with the same model (critical: query and document
  embeddings must live in the same vector space).
- ChromaDB returns the `top_k` most similar chunks (cosine similarity) from
  the selected domain's collection only.
- `llm.py` builds a prompt that presents each chunk as a **numbered
  excerpt** with its source/page, and instructs the model to answer *only*
  from that context and cite excerpt numbers — e.g. `[1]`. This is the
  anti-hallucination guardrail: if the context doesn't answer the question,
  the model is told to say so instead of guessing from general knowledge.
- The backend maps `[1]`/`[2]`/etc. back to real `source_file` +
  `page_number` and returns them alongside the answer, so the frontend can
  render clickable/expandable source citations under each reply.
- `LLM_PROVIDER` in `.env` picks Claude or Gemini; if the primary call fails
  and the other provider's key is configured, one fallback attempt is made
  automatically.

## Project structure

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

## Setup (Windows / PowerShell)

> **Important:** create this project **outside any OneDrive-synced folder**
> (e.g. `C:\dev\...`, not `C:\Users\<you>\OneDrive\...`) — OneDrive's live
> sync can corrupt `node_modules` mid-install.

```powershell
# 1. Create a local, non-OneDrive working directory and move into it
mkdir C:\dev
cd C:\dev

# 2. Copy/extract the rag-qa-chatbot folder here, then:
cd C:\dev\rag-qa-chatbot
```

### Backend

```powershell
cd C:\dev\rag-qa-chatbot\backend

# Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# If PowerShell blocks the activation script, run this once (as your user,
# not admin) and retry:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

pip install -r requirements.txt

# Configure API keys
copy .env.example .env
notepad .env    # paste your ANTHROPIC_API_KEY

# Run the server (first request will download the MiniLM model, ~80MB)
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` to see the interactive API docs and test
endpoints directly.

### Frontend

Open a **second** PowerShell window (leave the backend running):

```powershell
cd C:\dev\rag-qa-chatbot\frontend

npm install
copy .env.example .env    # only needed if backend runs on a non-default URL

npm run dev
```

Visit `http://localhost:5173`.

### Try it

1. In the sidebar, type a subject name (e.g. `DBMS`) and drop in a PDF.
2. Wait for the "indexed" confirmation.
3. Ask a question in the chat — the answer will cite `[1]`, `[2]`, etc.,
   with expandable source excerpts and page numbers underneath.

## Configuration reference (`backend/.env`)

| Variable | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `claude` | `claude` or `gemini` |
| `ANTHROPIC_API_KEY` | — | required if provider is `claude` |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Claude model id |
| `GEMINI_API_KEY` | — | optional fallback provider |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | local sentence-transformers model |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `150` | chunking parameters |
| `TOP_K` | `4` | chunks retrieved per question |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | ChromaDB storage path |
| `MAX_UPLOAD_MB` | `25` | upload size cap |

## Known limitations (good interview talking points)

- Scanned/image-only PDFs aren't handled — `pdfplumber` needs a text layer;
  OCR (e.g. `pytesseract`) would be the next step.
- Retrieval is pure vector similarity (no re-ranking or hybrid BM25+vector
  search yet) — fine for a college-scale corpus, but a larger corpus would
  benefit from a re-ranker.
- No conversation memory in the RAG prompt yet — each question is answered
  independently of prior chat turns; adding a condensed chat history to the
  prompt would enable follow-up questions like "what about the second one?".
