from __future__ import annotations

import json
import logging
import re
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from starlette.datastructures import UploadFile as StarletteUploadFile

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

GENERIC_PROMPT_WORDS = {
    "summarize",
    "summarise",
    "summary",
    "explain",
    "describe",
    "help",
    "detail",
    "details",
    "this",
    "that",
    "information",
    "info",
    "please",
    "expand",
    "clarify",
    "give",
    "tell",
}

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
async def general_chat(
    req: Request,
):

    attachments: List[dict[str, str]] = []

    if "multipart/form-data" in (req.headers.get("content-type") or "").lower():
        form = await req.form()
        payload_raw = form.get("payload")
        if payload_raw is None:
            raise HTTPException(status_code=400, detail="Missing payload field")
        try:
            data = json.loads(payload_raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}") from exc

        files = form.getlist("files")
        _logger.info("Form keys: %s", list(form.keys()))
        _logger.info("Received %d raw file objects", len(files))
        for file_obj in files:
            if not isinstance(file_obj, (UploadFile, StarletteUploadFile)):
                _logger.info("Skipping unexpected file object type: %s", type(file_obj))
                continue
            _logger.info("Processing attachment: %s (%s)", file_obj.filename, type(file_obj))
            try:
                contents = await file_obj.read()
            except Exception:
                continue
            if not contents:
                _logger.warning("Attachment %s was empty", file_obj.filename)
                continue
            text = BIPService.extract_text_from_upload(file_obj.filename, contents)
            _logger.info("Attachment %s extracted length %s", file_obj.filename, len(text or ""))
            if not text:
                _logger.warning("Attachment %s could not be parsed", file_obj.filename)
                continue
            attachments.append(
                {
                    "name": file_obj.filename,
                    "content": text.strip(),
                }
            )
        _logger.info("Received %s attachments with parsed content", len(attachments))
    else:
        try:
            data = await req.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    try:
        request = ChatRequest(**data)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc

    if not request.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    last_user = next((m for m in reversed(request.messages) if m.role == "user"), None)
    if last_user is None:
        raise HTTPException(status_code=400, detail="at least one user message is required")

    nodes: List = []
    system_messages: List[dict[str, str]] = []

    meaningful_tokens = [
        token
        for token in re.findall(r"[a-zA-Z0-9]+", last_user.content.lower())
        if len(token) >= 4 and token not in GENERIC_PROMPT_WORDS
    ]

    prompt_lower = last_user.content.lower()
    wants_summary = bool(re.search(r"summari[sz]e|summary", prompt_lower))
    refers_to_this = "this" in prompt_lower or "that" in prompt_lower

    if attachments:
        attachment_lines = []
        for attachment in attachments:
            snippet = attachment["content"] if len(attachment["content"]) <= 1200 else attachment["content"][:1200] + "…"
            attachment_lines.append(f"[Attachment: {attachment['name']}] {snippet}")
        attachment_block = "\n".join(attachment_lines)
        system_messages.append(
            {
                "role": "system",
                "content": (
                    "The user provided the following reference documents. Treat them as primary context."
                    " Summarise, paraphrase, or extract from these attachments exactly as requested."
                    " Only fall back to other knowledge if the attachments lack the necessary details.\n"
                    f"{attachment_block}"
                ),
            }
        )
    elif meaningful_tokens:
        similarity_floor = 0.55
        try:
            raw_nodes = rag_store.retrieve("general", last_user.content)
            nodes = [n for n in raw_nodes if getattr(n, "score", 0) >= similarity_floor]
            if not nodes and raw_nodes:
                nodes = raw_nodes[:2]
            if nodes:
                cite_block_lines = []
                for idx, node in enumerate(nodes, start=1):
                    source_name = node.node.metadata.get("source", "unknown")
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
        except CorpusNotReady:
            nodes = []
    else:
        if wants_summary and refers_to_this:
            return ChatResponse(
                response=(
                    "I can summarise an attachment or a specific policy. Upload the file you’d like summarised, "
                    "or mention the topic/document name, and I’ll take it from there."
                ),
                sources=[],
                mode="general",
            )
        return ChatResponse(
            response=(
                "I’m not sure what to summarise yet. Please mention a specific topic or attach a file, and I’ll help right away."
            ),
            sources=[],
            mode="general",
        )

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
