"""
文档处理智能体
负责处理文档文件，提取其中的内容和元数据。确保提取的全面和准确性，标准化输出格式
后续优化方向：
    1. 支持更多文件类型
    2. 根据文件特性增加ocr等功能。
"""

import sys
import traceback  # 新增：用于打印详细异常堆栈
from pathlib import Path
import yaml

from langchain_core.documents import Document  # 新增：用于文件路径校验
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from typing import TypedDict, Optional, Dict, Annotated
from langgraph.graph import StateGraph, END, START
from backend.agents.tools.tools import docproc_tool, qwen_tool


class DocProcState(TypedDict):
    """
    文档处理智能体的状态结构
    专注于文档解析结果.
    """
    input: Annotated[str, "用户输入"]
    file_path: Annotated[str, "文件路径"]
    file_type: Optional[Annotated[str, "文件类型"]]
    content: Optional[Annotated[str, "文件内容"]]
    metadata: Optional[Annotated[Dict, "文件元数据"]]
    error: Optional[Annotated[str, "错误信息"]]

#----------------------定义节点--------------------
def detect_document_format(state: DocProcState) -> DocProcState:
    """
    检测文档格式节点
    """
    try:
        file_ext = state["file_path"].split(".")[-1].lower()
        supported_types = ["doc", "docx", "pdf", "txt", "csv", "json"]
        if file_ext in supported_types:
            state["file_type"] = file_ext
        else:
            state["error"] = f"不支持的文件类型: {file_ext}"
    except Exception as e:
        state["error"] = f"文档格式检测失败: {str(e)}"
    return state


def extract_document_content(state: DocProcState) -> DocProcState:
    """
    提取文档内容节点
    """
    if state.get('error') or not state.get('file_type'):
        return state
    try:
        result = docproc_tool.invoke(
            state["file_path"]
        )
        if "content" not in result:
            state["error"] = "文档处理工具未返回内容"
            return state
        
        doc_list = result['content']
        if not isinstance(doc_list, list) or not all(isinstance(doc, Document) for doc in doc_list):
            state["error"] = "文档处理工具返回内容格式错误"
            return state

        page_contents = []
        for doc in doc_list:
            page_contents.append(doc.page_content)
            metadata = doc.metadata
        state["content"] = page_contents
        state["metadata"] = metadata
            
    except Exception as e:
        error_msg = f"文档内容提取失败: {str(e)}\n{traceback.format_exc()}"
        state["error"] = error_msg
    return state

def qwen_answer(state: DocProcState) -> DocProcState:

    prompt =  f"""
            你是一个文档处理智能体，仅基于以下文档内容回答用户问题，禁止编造信息：
            1. 用户问题：{state['input']}
            2. 文档内容：{state['content']}

            要求：
            - 若文档中无相关答案，需明确说明“文档中未找到相关内容”；
            - 若有相关答案，需引用文档原文。
        """

    with open("backend/config/model_settings.yaml", "r", encoding="utf-8") as f:
        model_settings = yaml.safe_load(f)
    default_model_config = model_settings.get("DEFAULT_MODEL")
    qwen_result = qwen_tool.invoke({
        "input": prompt,
        "img_path": '',  
        "model_name": default_model_config["llm_model"],
        "api_key": default_model_config["api_key"],
        "base_url": default_model_config["base_url"],
        "temperature": default_model_config["temperature"]
    })

    state["content"] = qwen_result['content']
    return state


# --------------------定义流程------------------
def create_docproc_agent():
    """
    创建文档处理智能体
    输出可直接作为后续融合流程的文档上下文来源
    """
    builder = StateGraph(DocProcState)

    #添加节点
    builder.add_node("detect_document_format", detect_document_format)
    builder.add_node("extract_document_content", extract_document_content)
    builder.add_node("qwen_answer", qwen_answer)

    #添加边
    builder.add_edge(START, "detect_document_format")
    builder.add_edge("detect_document_format", "extract_document_content")
    builder.add_edge("extract_document_content", "qwen_answer")
    builder.add_edge("qwen_answer", END)

    return builder.compile()

#使用示例
if __name__ == "__main__":
    doc_agent = create_docproc_agent()

    result = doc_agent.invoke({
        "input": "高龄孕妇的孕期保健?",
        "file_path": "test/孕前和孕期保健指南.doc"
    })
    # 输出结果（供后续智能体使用的格式）
    if result.get("error"):
        print(f"文档处理失败: {result['error']}")
    else:
        print({
            "source_type": "document",
            "file_type": result["file_type"],
            "content": result["content"],
            "metadata": result['metadata'],
        })
