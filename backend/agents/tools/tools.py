from langchain.tools import tool
from typing import Annotated, str, int

import base64

from backend.rag.retrieval import RAGRetrieval
from backend.knowledge_base.manage import KnowledgeBase
from backend.knowledge_base.loader import DocumentLoader

@tool(
    name_or_callable="rag_tool",
    description="根据用户问题检索指定知识库获取相关知识",
)
def rag_tool(
    user_query: Annotated[str, "用户的原始问题"], 
    vector_store_path: Annotated[str, "向量存储路径"],
    top_k: Annotated[int, "检索知识库的文档数量"] = 3,
) -> dict:
    """根据用户问题检索指定知识库获取相关知识"""
    if vector_store_path:
        retrieval = RAGRetrieval(persist_directory=vector_store_path)
    else:
        retrieval = RAGRetrieval()
    docs = retrieval.retrieve(user_query, top_k=top_k)
    knowledge_fragments = [{
        "source": doc.metadata.get('source'),
        "priority": doc.metadata.get('priority'),
        "content": doc.page_content
    }for doc in docs]
    return {"knowledge_fragments": knowledge_fragments}

@tool(
    name_or_callable="docproc_tool",
    description="处理.doc .txt .docx .excel .pdf文件，返回文件内容",
)
def docproc_tool(file_path: Annotated[str, "文件路径"]) -> dict:
    """处理.doc .txt .docx .excel .pdf文件，返回文件内容"""
    loader = DocumentLoader(file_path)
    docs = loader.load()
    return {"content": docs}

@tool(
    name_or_callable="imgproc_tool",
    description="处理图片文件，返回图片内容",
)
def imgproc_tool(file_path: Annotated[str, "图片文件路径"]) -> dict:
    """处理图片文件，返回图片内容"""
    

@tool(
    name_or_callable="save_memory",
    description="将对话记录保存到向量数据库中用于后续的语义检索",
)
def save_memory(chat_history: Annotated[list, "对话记录"], persist_directory: Annotated[str, "向量数据库路径"]) -> dict:
    """将对话记录保存到向量数据库中用于后续的语义检索"""
    kb = KnowledgeBase(
        data_root=chat_history,
        persist_directory=persist_directory,
    )
    kb.build_vector_store(rebuild=True)
    return {"status": "success"}
