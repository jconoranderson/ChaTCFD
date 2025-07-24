from llama_index.core import (
    SimpleDirectoryReader,          # ← changed
    VectorStoreIndex,               # ← changed
)
from llama_index.embeddings.ollama import OllamaEmbedding


DOC_DIR   = "docs/"                       # put PDFs or .txt files here
STORE_DIR = "rag_store"                   # where the vectors live

# helper: attach filename → {"source": "<file>"}
file_meta = lambda p: {"source": Path(p).name}

docs   = SimpleDirectoryReader("docs/").load_data()
embed  = OllamaEmbedding(model_name="mxbai-embed-large")
index  = VectorStoreIndex.from_documents(docs, embed_model=embed)
index.storage_context.persist("rag_store")
# build/refresh the index
embed  = OllamaEmbedding(model_name="mxbai-embed-large")
index  = VectorStoreIndex.from_documents(docs, embed_model=embed)
index.storage_context.persist(STORE_DIR)
