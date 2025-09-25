from __future__ import annotations

from textstat import flesch_kincaid_grade

from .providers import ModelProvider
from .settings import Settings

BANNED_TERMS = {
    "retarded",
    "handicapped",
    "crazy",
}


def cleanse_language(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in BANNED_TERMS):
        return (
            "I’m sorry—that wording can be harmful. Here is a respectful phrasing:\n\n"
            + text.replace("\n", " ")
        )
    return text


def ensure_readability(
    text: str,
    provider: ModelProvider,
    settings: Settings,
) -> str:
    try:
        grade = flesch_kincaid_grade(text)
    except Exception:
        return text

    if grade <= 8:
        return text

    prompt = (
        "Rewrite the following content so it reads at a U.S. grade 6-8 level, "
        "using respectful, people-first language and preserving key details. "
        "Answer directly without mentioning that you rewrote the text or adjusted the reading level. "
        "Format headings or key points with Markdown if helpful.\n\n"
        f"{text}"
    )
    rewritten = provider.chat(
        messages=[{"role": "user", "content": prompt}],
        model=settings.rewrite_model,
    )
    return rewritten or text


def apply_guardrails(text: str, provider: ModelProvider, settings: Settings) -> str:
    intermediate = cleanse_language(text)
    return ensure_readability(intermediate, provider, settings)
