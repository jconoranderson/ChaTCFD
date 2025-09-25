# ChaTCFD Complete

Unified local-first assistant combining the existing ChaTCFD concierge, benefits navigator, and BIP generator into a single project. Designed to run comfortably on a 2023 MacBook Pro (18 GB RAM) using open-weight models served by Ollama, with an easy pathway to migrate to hosted OpenAI APIs for production.

## Project Layout

```
ChaTCFD_Complete/
├── backend/
│   ├── app/               # FastAPI application (chat + benefits + BIP endpoints)
│   ├── ingest/            # Utilities for building vector stores
│   ├── data/              # Source documents (place your policies & examples here)
│   ├── storage/           # Persisted vector stores (auto-created)
│   └── requirements.txt   # Python dependencies
└── frontend/              # React + Tailwind interface with three assistant views
```

## Local Model Recommendation

For a MacBook Pro (18 GB RAM), use a quantised open-weight model via [Ollama](https://ollama.ai):

```bash
ollama pull llama3.1:8b-instruct-q4_0   # balanced quality ↔ footprint (~5.5 GB)
ollama pull nomic-embed-text             # embeddings for the RAG indexes
```

The defaults in `backend/app/settings.py` target Ollama at `http://localhost:11434`. Adjust `DEFAULT_CHAT_MODEL`, `REWRITE_MODEL`, or `EMBED_MODEL` through environment variables if you prefer lighter models (e.g. `phi3:mini`).

When you later adopt hosted OpenAI endpoints, set `MODEL_PROVIDER=openai`, `OPENAI_API_KEY`, and `OPENAI_BASE_URL` (if using the responses API) without changing application code.

## Preparing the Knowledge Bases

Copy your existing source content into the new data folders:

- General policies, procedures → `backend/data/general/`
- Benefits guidebook or PDFs → `backend/data/benefits/`
- BIP examples (`*.txt`) → `backend/data/bip_examples/`
- BIP policy references → `backend/data/bip_policies/`

Then build or rebuild the vector stores:

```bash
cd backend
python -m ingest.ingest --corpus all
```

Re-run the command whenever you update documents.

## Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Environment variables (optional) can be placed in `backend/.env`:

```
MODEL_PROVIDER=ollama
DEFAULT_CHAT_MODEL=llama3.1
REWRITE_MODEL=llama3.1
EMBED_MODEL=nomic-embed-text
CORS_ALLOW_ORIGINS=http://localhost:5173
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The interface exposes three tabs:

1. **TCFD Concierge** – General assistant with document citations and guard rails.
2. **Benefits Advisor** – Benefits-focused Q&A with retrieval from the guidebook corpus.
3. **Behavior Plan Studio** – Upload FBAs and generate BIPs with policy-aligned prompts.

Set `VITE_API_BASE_URL` in a `.env.local` file if your backend runs on a different host/port.

## Next Steps

- Tune prompts and guard-rails per department before production rollout.
- Add authentication (e.g. Auth0, Azure AD) around the FastAPI app for internal deployment.
- When ready for hosted inference, point `MODEL_PROVIDER=openai` and supply the appropriate API credentials.
