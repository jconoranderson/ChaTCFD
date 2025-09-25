from __future__ import annotations

import logging
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .bip import BIPService
from .guardrails import apply_guardrails
from .providers import ModelProvider, ModelProviderError
from .rag import CorpusNotReady, RAGStore
from .schemas import (
    BIPResponse,
    ChatRequest,
    ChatResponse,
    SourceDocument,
)
from .settings import Settings, get_settings

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

app = FastAPI(title="ChaTCFD Complete", version="0.1.0")

settings: Settings = get_settings()
provider = ModelProvider(settings)
rag_store = RAGStore(settings)
bip_service = BIPService(settings, provider, rag_store)

cors_origins = settings.origins_list()
allow_credentials = True
if "*" in cors_origins:
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_preflight(request, call_next):
    if request.method == "OPTIONS":
        _logger.info(
            "CORS preflight from %s with method %s and headers %s",
            request.headers.get("origin"),
            request.headers.get("access-control-request-method"),
            request.headers.get("access-control-request-headers"),
        )
    return await call_next(request)


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


def _prepare_payload(messages) -> List[dict[str, str]]:
    return [{"role": m.role, "content": m.content} for m in messages]


def _format_sources(nodes) -> List[SourceDocument]:
    formatted: List[SourceDocument] = []
    for idx, node in enumerate(nodes, start=1):
        try:
            metadata = node.node.metadata or {}
            source_name = metadata.get("source") or metadata.get("file_name") or "unknown"
            snippet = node.node.get_content().strip()
            formatted.append(SourceDocument(file=source_name, snippet=snippet[:240]))
        except AttributeError:
            continue
    return formatted


@app.post("/chat/general", response_model=ChatResponse)
def general_chat(
    request: ChatRequest,
):

    if not request.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    last_user = next((m for m in reversed(request.messages) if m.role == "user"), None)
    if last_user is None:
        raise HTTPException(status_code=400, detail="at least one user message is required")

    nodes = []
    system_messages: List[dict[str, str]] = []
    similarity_floor = 0.55
    try:
        raw_nodes = rag_store.retrieve("general", last_user.content)
        nodes = [n for n in raw_nodes if getattr(n, "score", 0) >= similarity_floor]
        if not nodes and raw_nodes:
            nodes = raw_nodes[:2]
        if nodes:
            cite_block_lines = []
            for idx, node in enumerate(nodes, start=1):
                source_name = node.node.metadata.get('source', 'unknown')
                content = node.node.get_content().strip()
                snippet = content if len(content) <= 1200 else content[:1200] + "…"
                cite_block_lines.append(f"[{idx}] {source_name}: {snippet}")
            cite_block = "\n".join(cite_block_lines)
            system_messages.append(
                {
                    "role": "system",
                    "content": (
                        "You are ChaTCFD, an assistant for The Center for Discovery staff. Prefer the following internal references when they address the question, and cite them inline."
                        " When the excerpts describe frameworks (e.g., the Centerwide 4 C's or SynergE6), explicitly list every component mentioned and summarise each using the provided wording."
                        " Do not omit any bullet or numbered item that appears in the excerpts."
                        " If the user asks for application, coaching, or next steps, combine the referenced material with safe, evidence-informed autism support practices rather than declining."
                        " When you mention an organisation, resource, or programme, include its official website URL using Markdown link format (e.g., [Autism Society](https://autismsociety.org))."
                        " Only reply 'I couldn't find that in the documentation' when no relevant information and no responsible guidance can be given.\n"
                        f"{cite_block}\n--- end references ---"
                    ),
                }
            )
        else:
            nodes = []
    except CorpusNotReady:
        nodes = []

    payload = system_messages + _prepare_payload(request.messages)

    try:
        raw_response = provider.chat(payload, model=request.model)
    except ModelProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    guarded = apply_guardrails(raw_response, provider, settings)

    return ChatResponse(
        response=guarded,
        sources=[],
        mode="general",
    )


@app.post("/chat/benefits", response_model=ChatResponse)
def benefits_chat(
    request: ChatRequest,
):

    if not request.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    last_user = next((m for m in reversed(request.messages) if m.role == "user"), None)
    if last_user is None:
        raise HTTPException(status_code=400, detail="at least one user message is required")

    try:
        nodes = rag_store.retrieve("benefits", last_user.content)
    except CorpusNotReady:
        nodes = []

    context_block = "\n\n".join(
        node.node.get_content().strip()
        for node in nodes
        if node.node and node.node.get_content()
    )
    if not context_block:
        context_block = "[No relevant context retrieved]"

    history_lines = [
        f"{('User' if msg.role == 'user' else 'Assistant')}: {msg.content}"
        for msg in request.messages[:-1]
        if msg.role in {"user", "assistant"}
    ]
    history_excerpt = "\n".join(history_lines[-6:])

    system_prompt = (
        "You are the benefits assistant for The Center for Discovery. Answer confidently, "
        "clearly, and concisely using only the provided context. If information is missing, "
        "reply with: 'I couldn't find that in the documentation.'"
        " When you reference an organisation or resource that has a public website, include the official URL using Markdown link format (e.g., [Autism Speaks](https://autismspeaks.org))."
    )

    user_payload = (
        (f"Conversation so far:\n{history_excerpt}\n\n" if history_excerpt else "")
        + f"Context:\n{context_block}\n\nMost recent question: {last_user.content}"
    )

    augmented = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_payload},
    ]

    try:
        raw_response = provider.chat(augmented, model=request.model)
    except ModelProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    guarded = apply_guardrails(raw_response, provider, settings)

    return ChatResponse(
        response=guarded,
        sources=[],
        mode="benefits",
    )


@app.post("/bip/generate", response_model=BIPResponse)
async def generate_bip(
    name: str = Form(...),
    age: int = Form(...),
    diagnosis: str = Form(...),
    behavior: str = Form(...),
    setting: str = Form(...),
    trigger: str = Form(...),
    notes: str | None = Form(None),
    model: str | None = Form(None),
    fba_file: UploadFile | None = File(None),
):
    fba_text: str | None = None
    if fba_file is not None:
        contents = await fba_file.read()
        extracted = bip_service.extract_text_from_upload(fba_file.filename, contents)
        if extracted is None:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, or TXT.")
        fba_text = extracted

    prompt = bip_service.build_prompt(
        name=name,
        age=age,
        diagnosis=diagnosis,
        behavior=behavior,
        setting=setting,
        trigger=trigger,
        notes=notes,
        fba_text=fba_text,
    )

    try:
        bip_text = bip_service.generate(prompt, model_override=model)
    except ModelProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return BIPResponse(bip=bip_text)
