from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import requests
from requests import Response

from .settings import Settings

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore

_logger = logging.getLogger(__name__)


class ModelProviderError(RuntimeError):
    pass


class ModelProvider:
    """Thin abstraction over different inference backends."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._openai_client: Optional[OpenAI] = None

        if settings.model_provider == "openai":
            if OpenAI is None:
                raise ModelProviderError(
                    "openai python package is required when MODEL_PROVIDER=openai"
                )
            if not settings.openai_api_key:
                raise ModelProviderError("OPENAI_API_KEY must be set for OpenAI provider")
            self._openai_client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url or "https://api.openai.com/v1",
            )

    def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> str:
        provider = self.settings.model_provider.lower()
        model_name = model or self.settings.default_model

        if provider == "ollama":
            return self._chat_with_ollama(messages, model_name)
        if provider == "openai":
            return self._chat_with_openai(messages, model_name)

        raise ModelProviderError(f"Unsupported model provider: {provider}")

    # ---- Ollama ----
    def _chat_with_ollama(self, messages: List[Dict[str, str]], model: str) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/chat"
        try:
            response = requests.post(url, json=payload, timeout=self.settings.request_timeout)
        except requests.RequestException as exc:
            raise ModelProviderError(f"Ollama request failed: {exc}") from exc

        content = self._extract_ollama_content(response)
        if content is None:
            raise ModelProviderError(
                f"Unexpected Ollama response: {response.status_code} {response.text[:200]}"
            )
        return content

    @staticmethod
    def _extract_ollama_content(response: Response) -> Optional[str]:
        if not response.ok:
            _logger.error("Ollama error %s: %s", response.status_code, response.text[:200])
            return None
        try:
            data = response.json()
        except json.JSONDecodeError:
            return None

        message = data.get("message") or {}
        content = message.get("content")
        return content

    # ---- OpenAI ----
    def _chat_with_openai(self, messages: List[Dict[str, str]], model: str) -> str:
        if self._openai_client is None:  # pragma: no cover - guarded above
            raise ModelProviderError("OpenAI client not initialised")

        formatted = [
            {
                "role": msg["role"],
                "content": msg["content"],
            }
            for msg in messages
        ]

        try:
            response = self._openai_client.responses.create(
                model=model,
                input=formatted,
            )
        except Exception as exc:  # broad catch to surface provider errors cleanly
            raise ModelProviderError(f"OpenAI request failed: {exc}") from exc

        # Concatenate any text segments returned
        try:
            return response.output_text  # type: ignore[attr-defined]
        except AttributeError:
            # Fallback for SDKs exposing output as list of content blocks
            chunks: List[str] = []
            for item in getattr(response, "output", []) or []:
                if getattr(item, "type", None) == "output_text":
                    chunks.append(getattr(item, "text", ""))
            payload = "".join(chunks)
            if not payload:
                raise ModelProviderError("OpenAI response missing text content")
            return payload
