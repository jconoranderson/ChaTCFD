from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application configuration sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    model_provider: str = Field("ollama", validation_alias="MODEL_PROVIDER")
    default_model: str = Field("llama3.1", validation_alias="DEFAULT_CHAT_MODEL")
    rewrite_model: str = Field("llama3.1", validation_alias="REWRITE_MODEL")
    embed_model: str = Field("nomic-embed-text", validation_alias="EMBED_MODEL")

    ollama_base_url: str = Field(
        "http://localhost:11434",
        validation_alias="OLLAMA_BASE_URL",
    )

    openai_base_url: str | None = Field(None, validation_alias="OPENAI_BASE_URL")
    openai_api_key: str | None = Field(None, validation_alias="OPENAI_API_KEY")

    vector_store_dir: str = Field(
        default=str(BACKEND_DIR / "storage"),
        validation_alias="VECTOR_STORE_DIR",
    )

    general_docs_dir: str = Field(
        default=str(BACKEND_DIR / "data" / "general"),
        validation_alias="GENERAL_DOCS_DIR",
    )

    benefits_docs_dir: str = Field(
        default=str(BACKEND_DIR / "data" / "benefits"),
        validation_alias="BENEFITS_DOCS_DIR",
    )

    bip_examples_dir: str = Field(
        default=str(BACKEND_DIR / "data" / "bip_examples"),
        validation_alias="BIP_EXAMPLES_DIR",
    )

    bip_policies_dir: str = Field(
        default=str(BACKEND_DIR / "data" / "bip_policies"),
        validation_alias="BIP_POLICIES_DIR",
    )

    general_top_k: int = Field(3, validation_alias="GENERAL_TOP_K")
    benefits_top_k: int = Field(3, validation_alias="BENEFITS_TOP_K")
    bip_top_k: int = Field(4, validation_alias="BIP_TOP_K")

    request_timeout: int = Field(120, validation_alias="MODEL_REQUEST_TIMEOUT")
    max_retries: int = Field(2, validation_alias="MODEL_MAX_RETRIES")

    cors_allow_origins: str = Field(
        "http://localhost:5173,http://127.0.0.1:5173,http://0.0.0.0:5173",
        validation_alias="CORS_ALLOW_ORIGINS",
    )

    def origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
