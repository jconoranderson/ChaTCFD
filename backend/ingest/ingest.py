from __future__ import annotations

import argparse

from app.rag import CorpusNotReady, RAGStore
from app.settings import Settings, get_settings


def rebuild_corpus(rag_store: RAGStore, corpus: str) -> None:
    try:
        rag_store.rebuild(corpus)
        print(f"✅ Rebuilt corpus '{corpus}'")
    except CorpusNotReady as exc:
        print(f"⚠️  Skipped '{corpus}': {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild ChaTCFD vector stores")
    parser.add_argument(
        "--corpus",
        choices=["general", "benefits", "bip_policies", "all"],
        default="all",
        help="Corpus to rebuild",
    )
    args = parser.parse_args()

    settings: Settings = get_settings()
    rag_store = RAGStore(settings)

    targets = (
        [args.corpus]
        if args.corpus != "all"
        else ["general", "benefits", "bip_policies"]
    )

    for corpus in targets:
        rebuild_corpus(rag_store, corpus)


if __name__ == "__main__":
    main()
