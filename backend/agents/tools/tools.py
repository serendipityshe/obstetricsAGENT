from langchain.tools import tool
from typing import Annotated

import base64

from backend.rag.retrieval import RAGRetrieval
from backend.knowledge_base.manage import KnowledgeBase
from backend.knowledge_base.loader import DocumentLoader
from backend.llm.openai_wrapper import QwenAIWrap

@tool(
    name_or_callable="qwen_tool",
    description="调用qwen模型",
)
def qwen_tool(
    query: Annotated[str, "用户的原始问题"],
    model_name: Annotated[str, "模型名称"],
    api_key: Annotated[str, "模型api密钥"],
    base_url: Annotated[str, "模型地址"],
    temperature: Annotated[int, "模型温度"]
) -> dict:
    """调用qwen模型"""
    qwen = QwenAIWrap(
        model_name = model_name, 
        api_key = api_key, 
        base_url = base_url, 
        temperature = temperature)
    response = qwen.invoke(query)
    return {"content": response}

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
    """处理.doc .txt .docx .excel .pdf .json文件，返回文件内容"""
    loader = DocumentLoader(file_path)
    docs = loader.load()
    return {"content": docs}

@tool(
    name_or_callable="imgproc_tool",
    description="处理图片文件，返回base64编码内容（用于大模型解析图片）",
)
def imgproc_tool(file_path: Annotated[str, "图片文件路径"]) -> dict:
    """处理图片文件，返回base64编码内容"""
    try:
        with open(file_path, "rb") as image_file:
            # 读取图片二进制内容并转为base64
            base64_str = base64.b64encode(image_file.read()).decode("utf-8")
        return {
            "status": "success",
            "content": base64_str,
            "file_path": file_path
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"图片处理失败: {str(e)}"
        }
    

@tool(
    name_or_callable="save_memory",
    description="将对话记录保存到向量数据库中用于后续的语义检索",
)
def save_memory(chat_history: Annotated[str, "对话记录路径"], persist_directory: Annotated[str, "向量数据库路径"]) -> dict:
    """将对话记录保存到向量数据库中用于后续的语义检索"""
    kb = KnowledgeBase(
        data_root=chat_history,
        persist_directory=persist_directory,
    )
    kb.build_vector_store(rebuild=True)
    return {"status": "success"}
