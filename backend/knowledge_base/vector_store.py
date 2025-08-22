'''
向量数据库

TO DO:
1. 文本向量化
2. 语义检索引擎

DONE:
1. 文本向量化
'''

from typing import *
from langchain.schema import Document
from langchain_chroma import Chroma
from .embedder import EmbeddingModel


class ChromaVectorStore:
    def __init__(self, documents : List[Document], embeddings : EmbeddingModel, persist_directory : str):
        self.documents = documents
        self.embeddings = embeddings
        self.persist_directory = persist_directory
        self.vector_store = Chroma.from_documents(
            self.documents,
            self.embeddings,
            persist_directory = self.persist_directory
        )

    def search(self, query : str, top_k : int = 5):
        results = self.vector_store.similarity_search(query, top_k)
        return results
