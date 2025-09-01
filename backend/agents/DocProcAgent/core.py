"""
文档处理智能体
负责处理文档文件，提取其中的内容和元数据。确保提取的全面和准确性，标准化输出格式
后续优化方向：
    1. 支持更多文件类型
    2. 根据文件特性增加ocr等功能。
"""

from typing import TypedDict, Optional, Dict, Annotated
from langgraph.graph import StateGraph, END, START
from backend.agents.tools.tools import docproc_tool


class DocProcState(TypedDict):
    """
    文档处理智能体的状态结构
    专注于文档解析结果.
    """
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
    if state["error"] or not state["file_type"]:
        return state
    try:
        result = docproc_tool(
            state["file_path"]
        )
        if "content" in result:
            state["content"] = result["content"]
        else:
            state["error"] = "文档处理工具未返回内容"
    except Exception as e:
        state["error"] = f"文档内容提取失败: {str(e)}"
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

    #添加边
    builder.add_edge(START, "detect_document_format")
    builder.add_edge("detect_document_format", "extract_document_content")
    builder.add_edge("extract_document_content", END)

    return builder.compile()

#使用示例
if __name__ == "__main__":
    doc_agent = create_docproc_agent()

    result = doc_agent.invoke({
        "file_path": "medical_record.pdf"
    })
    # 输出结果（供后续智能体使用的格式）
    if result["error"]:
        print(f"文档处理失败: {result['error']}")
    else:
        print({
            "source_type": "document",
            "file_type": result["file_type"],
            "content": result["content"],
            "metadata": result["metadata"]
        })
