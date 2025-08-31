'''
rag检索


'''

from typing import List
from langchain_core.documents import Document
from backend.knowledge_base.manage import KnowledgeBase

import yaml

class RAGRetrieval:
    '''rag检索类
    Args:
        persist_directory (str): 向量存储路径
        data_root (str): 文档加载路径
    Returns:
        List[Document]: 文档列表
    '''
    def __init__(self, persist_directory : str = 'data/vector_store_json', data_root : str = "data/raw_manuals"):
        self.knowledge_base = KnowledgeBase(
            data_root=data_root,
            persist_directory=persist_directory,
        )
        self.knowledge_base.build_vector_store(rebuild=False)

    def retrieve(self, query : str, top_k : int = 5, priority_weight : float = 0.2) -> List[Document]:
        docs_with_scores = self.knowledge_base.vector_store.similarity_search_with_score(query, k = top_k * 2)

        scored_results = []

        for doc, score in docs_with_scores:
            priority = doc.metadata.get('priority', 3)
            weight = 1.0 + priority_weight * (3 - priority)
            weight_score = score * weight
            scored_results.append((doc, weight_score))
        
        scored_results.sort(key=lambda x : x[1], reverse= True)
        return [doc for doc, _ in scored_results[:top_k]]