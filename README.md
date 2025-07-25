# ChaTCFD
Purpose built language model to serve the specific needs of The Center for Discovery, adhering to local regulation and the principals of the Organization #WhatHappensHereMattersEverywhere

A general putpose LLM tailored speficically for the needs of The Center for Discovery, a speciflist care facility for individuals with complex cognitive disorders, using prompt orchestration with retrieval-augmented context (RAG).

- **Ollama** for local LLM inference  
- **RAG (Retrieval-Augmented Generation)** with `llama-index`  
- **IDD-safe output filter** for respectful, simplified responses  
- A **modern front-end** (served via `dist/`) for user interaction

Features
--------

- **FastAPI backend** with `/chat` endpoint
- **Vector-based retrieval** for contextual answers (using `llama-index`)
- **Automatic readability adjustment** (US Grade 6–8)
- **People-first language filtering**
- **Static front-end hosting** (SPA-ready)
- **Environment-based configuration**

Getting Started
---------------

### 1. Install Dependencies

```bash
pip install fastapi uvicorn requests textstat llama-index ollama-python
```

### 2. Run the Backend

```bash
uvicorn main:app --reload
```

The API will be available at: http://localhost:8000  
Static front-end served at: `/`

Environment Variables (Optional)
--------------------------------

You can customize the behavior with these variables:

| Variable               | Default Value                        | Description |
|------------------------|--------------------------------------|-------------|
| `OLLAMA_URL`           | `http://localhost:11434/api/chat`    | URL of Ollama API |
| `VECTOR_STORE_DIR`     | `./rag_store`                        | Path to vector store for RAG |
| `RETRIEVER_TOP_K`      | `3`                                  | Number of retrieved chunks |
| `OLLAMA_MODEL_FALLBACK`| `tcfd-mistral`                       | Model used for rewriting text |

API Overview
------------

### POST `/chat`

**Request:**
```json
{
  "model": "tcfd-mistral",
  "messages": [
    {"role": "user", "content": "Explain TCFD briefly"}
  ]
}
```

**Response:**
```json
{
  "response": "Simplified and safe response here...",
  "sources": [
    {"file": "document.pdf", "snippet": "Relevant excerpt..."}
  ]
}
```

Front-End Integration
---------------------

- The **frontend build** (e.g., Vite/React/Svelte) should be placed in `dist/`
- FastAPI serves it at root `/`
- CORS enabled for `http://localhost:5173` during dev mode

Development Notes
-----------------

- RAG is **lazy-initialized**: if `rag_store` is missing, app runs without retrieval
- Filtering enforces **respectful phrasing** (`retarded`, `crazy`, etc., are replaced)
- Text simplification uses **fallback model** via Ollama for grade-level rewriting

Example `.gitignore`
---------------------

Ensure Python caches and build files are ignored:
```
__pycache__/
*.pyc
dist/
env/
.venv/
```

Future Enhancements
-------------------

- Streaming responses (`async` + `sse`)
- Multi-model switching
- UI improvements for source citations
