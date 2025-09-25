from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List

from llama_index.core import (
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.schema import NodeWithScore
from llama_index.embeddings.ollama import OllamaEmbedding

from .settings import Settings

_logger = logging.getLogger(__name__)


class CorpusNotReady(RuntimeError):
    pass


class RAGStore:
    """Lazy loader for vector stores backed by llama-index."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._retrievers: Dict[str, Any] = {}
        self._index_meta: Dict[str, Dict[str, Path]] = {}

    def _embed_model(self) -> OllamaEmbedding:
        base_url = self.settings.ollama_base_url.rstrip("/")
        return OllamaEmbedding(
            model_name=self.settings.embed_model,
            base_url=base_url,
        )

    def _store_dir(self, corpus: str) -> Path:
        return Path(self.settings.vector_store_dir) / corpus

    def _data_dir(self, corpus: str) -> Path:
        mapping = {
            "general": Path(self.settings.general_docs_dir),
            "benefits": Path(self.settings.benefits_docs_dir),
            "bip_policies": Path(self.settings.bip_policies_dir),
        }
        return mapping[corpus]

    def _top_k(self, corpus: str) -> int:
        if corpus == "general":
            return self.settings.general_top_k
        if corpus == "benefits":
            return self.settings.benefits_top_k
        if corpus == "bip_policies":
            return self.settings.bip_top_k
        return 3

    def _load_index(self, corpus: str) -> VectorStoreIndex:
        store_dir = self._store_dir(corpus)
        store_dir.mkdir(parents=True, exist_ok=True)

        embed_model = self._embed_model()

        if (store_dir / "docstore.json").exists():
            storage_context = StorageContext.from_defaults(persist_dir=str(store_dir))
            return load_index_from_storage(storage_context, embed_model=embed_model)

        data_dir = self._data_dir(corpus)
        if not data_dir.exists() or not any(data_dir.iterdir()):
            raise CorpusNotReady(
                f"No source documents found for corpus '{corpus}' in {data_dir}."
            )

        docs = SimpleDirectoryReader(str(data_dir)).load_data()
        index = VectorStoreIndex.from_documents(docs, embed_model=embed_model)
        index.storage_context.persist(persist_dir=str(store_dir))
        return index

    def retriever(self, corpus: str):  # type: ignore[override]
        if corpus not in self._retrievers:
            index = self._load_index(corpus)
            self._retrievers[corpus] = index.as_retriever(similarity_top_k=self._top_k(corpus))
        return self._retrievers[corpus]

    def retrieve(self, corpus: str, query: str) -> List[NodeWithScore]:
        retriever = self.retriever(corpus)
        try:
            return retriever.retrieve(query)
        except Exception as exc:
            _logger.error("RAG retrieval failed for %s: %s", corpus, exc)
            raise

    def rebuild(self, corpus: str) -> None:
        store_dir = self._store_dir(corpus)
        if store_dir.exists():
            for item in store_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        if corpus in self._retrievers:
            del self._retrievers[corpus]
        self._load_index(corpus)
