from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    allow_generalization: bool = False


class SourceDocument(BaseModel):
    file: str
    snippet: str


class ChatResponse(BaseModel):
    response: str
    sources: List[SourceDocument] = []
    mode: str


class BIPRequest(BaseModel):  # Used for OpenAPI schema; actual endpoint uses multipart form
    name: str
    age: int
    diagnosis: str
    behavior: str
    setting: str
    trigger: str
    notes: Optional[str] = None


class BIPResponse(BaseModel):
    bip: str
