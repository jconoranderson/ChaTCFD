"""
main.py  –  FastAPI + Ollama + RAG + IDD-safe output filter
-----------------------------------------------------------
  • GETTING STARTED
        pip install fastapi uvicorn requests textstat llama-index ollama-python
        uvicorn main:app --reload
  • OPTIONAL ENV VARS
        OLLAMA_URL        default http://localhost:11434/api/chat
        VECTOR_STORE_DIR  default ./rag_store
        RETRIEVER_TOP_K   default 3
        OLLAMA_MODEL_FALLBACK  model used for rewriting (default tcfd-mistral)
"""

import os, requests
import traceback, logging

from typing import List, Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from textstat import flesch_kincaid_grade

# ───────── Llama-Index for RAG ─────────
from llama_index.core import (       
    StorageContext,
    load_index_from_storage,
)

from llama_index.core.schema import TextNode
from llama_index.embeddings.ollama import OllamaEmbedding

# add once in main.py (top of file)
from fastapi.staticfiles import StaticFiles

# ───────── FASTAPI bootstrap ──────────
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)

# ───────── Pydantic schemas ───────────
class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]

# ───────── Runtime config ─────────────
OLLAMA_URL     = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
STORE_DIR      = os.getenv("VECTOR_STORE_DIR", "rag_store")
TOP_K          = int(os.getenv("RETRIEVER_TOP_K", 1))
REWRITE_MODEL  = os.getenv("OLLAMA_MODEL_FALLBACK", "tcfd-mistral")

# ───────── RAG initialisation (lazy-safe) ─────────
if os.path.isdir(STORE_DIR):
    storage_ctx = StorageContext.from_defaults(persist_dir=STORE_DIR)

    # ← choose the same model you used in embed_docs.py
    embed_model = OllamaEmbedding(model_name="mxbai-embed-large")  

    index     = load_index_from_storage(storage_ctx, embed_model=embed_model)
    retriever = index.as_retriever(similarity_top_k=TOP_K)
else:
    index = retriever = None


# ───────── Output guard rails ─────────
BANNED_WORDS = {"retarded", "handicapped", "crazy"}

def simplify(text: str) -> str:
    """Ask Ollama to rewrite at grade-6–8 level if original is complex."""
    payload = {
        "model": REWRITE_MODEL,
        "messages": [
            {"role": "user",
             "content": ("Rewrite the following so it reads at a U.S. grade-6–8 "
                         "level and removes jargon:\n\n" + text)}
        ],
        "stream": False
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=90)
        if r.ok:
            return r.json().get("message", {}).get("content", text)
    except Exception:
        pass
    return text  # fall back to original on any failure

def guard(text: str) -> str:
    """Enforce people-first language and readability."""
    if any(bad in text.lower() for bad in BANNED_WORDS):
        text = ("I’m sorry—that wording can be hurtful. "
                "Here is a respectful phrasing:\n\n" + text.replace("\n", " "))
    try:
        if flesch_kincaid_grade(text) > 8:
            text = simplify(text)
    except Exception:
        pass
    return text

# ───────── Prompt augmentation ────────
def inject_context(chain: List[Message]) -> (List[dict], List[TextNode]):
    """
    • Inserts a SYSTEM message containing top-k retrieved chunks
      right before the last user turn.
    • Returns both the new message list and the nodes for source reporting.
    """
    if retriever is None:
        return [m.dict() for m in chain], []

    last_user = next((m for m in reversed(chain) if m.role == "user"), None)
    if not last_user or retriever is None:
        return [m.dict() for m in chain], []

    # ⬇️  NEW early-exit: very short questions
    if len(last_user.content.split()) <= 3:
        return [m.dict() for m in chain], []

    # retrieve and filter by similarity
    raw_nodes = retriever.retrieve(last_user.content)
    nodes = [n for n in raw_nodes if n.score >= 0.75]

    if not nodes:                       # nothing relevant → no injection
        return [m.dict() for m in chain], []

    cite_block = "\n".join(
        f"[{i+1}] {n.node.metadata.get('source', 'unknown')}: "
        f"{n.node.get_content()[:160].strip()}..."
        for i, n in enumerate(nodes)
    )
    system_msg = {
        "role": "system",
        "content": ("The following excerpts are authoritative sources; cite them "
                    "where relevant.\n" + cite_block + "\n--- end excerpts ---\n")
    }

    augmented = []
    for m in chain:
        if m is last_user:
            augmented.append(system_msg)
        augmented.append(m.dict())
    return augmented, nodes

# ───────── /chat endpoint ─────────────
@app.post("/chat")
def chat_with_model(req: ChatRequest):
    try:
        messages, src_nodes = inject_context(req.messages)
        payload = {
            "model":   "mistral",
            "messages": messages,
            "stream":   False
        }

        logging.info("▶︎ sending to Ollama: %s", payload["model"])
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
        logging.info("◀︎ status %s – body: %s", r.status_code, r.text[:300])

        if not r.ok:
            raise HTTPException(status_code=r.status_code, detail=r.text)

        raw  = r.json().get("message", {}).get("content", "")
        safe = guard(raw)
        sources = [
            {"file": n.node.metadata.get("source", "unknown"),
             "snippet": n.node.get_content()[:160].strip()}
            for n in src_nodes
        ]
        return {"response": safe, "sources": sources}

    except Exception as e:
        # print full traceback to console so we can see the root cause
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
