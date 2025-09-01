"""
混合智能体
负责对齐DocProcAgent, ImgProcAgent, MeMAgent的输出格式，整合成统一结构供检索智能体使用
"""
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from typing import TypedDict, Optional, List, Annotated
from langgraph.graph import StateGraph, END, START
from backend.agents.DocProcAgent.core import create_docproc_agent
from backend.agents.ImgProcAgent.core import create_imgproc_agent
from backend.agents.MeMAgent.core import create_mem_agent


class MixAgentState(TypedDict):
    """混合智能体状态"""
    # 输入参数
    doc_file_path: Optional[Annotated[str, "文档路径"]]
    img_file_path: Optional[Annotated[str, "图片路径"]]
    chat_history: Annotated[list, "聊天历史"]
    persist_directory: Annotated[str, "长期记忆存储目录"]
    
    # 中间结果
    doc_result: Optional[Annotated[dict, "文档处理结果"]]
    img_result: Optional[Annotated[dict, "图片处理结果"]]
    mem_result: Optional[Annotated[dict, "记忆处理结果"]]
    
    # 输出结果
    combined_results: Annotated[List[dict], "统一格式的结果列表"]
    error: Optional[Annotated[str, "错误信息"]]


# 节点：处理文档
def process_document(state: MixAgentState) -> MixAgentState:
    if not state["doc_file_path"]:
        return state
    try:
        doc_agent = create_docproc_agent()
        result = doc_agent.invoke({"file_path": state["doc_file_path"]})
        if result["error"]:
            state["error"] = f"文档处理错误: {result['error']}"
            return state
        # 统一格式
        state["doc_result"] = {
            "source_type": "document",
            "file_type": result["file_type"],
            "content": result["content"],
            "metadata": result["metadata"] or {}
        }
    except Exception as e:
        state["error"] = f"文档处理节点异常: {str(e)}"
    return state


# 节点：处理图片
def process_image(state: MixAgentState) -> MixAgentState:
    if not state["img_file_path"]:
        return state
    try:
        img_agent = create_imgproc_agent()
        result = img_agent.invoke({"file_path": state["img_file_path"]})
        if result["error"]:
            state["error"] = f"图片处理错误: {result['error']}"
            return state
        # 统一格式
        state["img_result"] = {
            "source_type": "image",
            "file_type": state["img_file_path"].split(".")[-1].lower(),  # 从路径提取格式
            "content": result["content"],
            "metadata": result["metadata"] or {}
        }
    except Exception as e:
        state["error"] = f"图片处理节点异常: {str(e)}"
    return state


# 节点：处理记忆
def process_memory(state: MixAgentState) -> MixAgentState:
    try:
        mem_agent = create_mem_agent()
        result = mem_agent.invoke({
            "chat_history": state["chat_history"],
            "persist_directory": state["persist_directory"]
        })
        if result["error"]:
            state["error"] = f"记忆处理错误: {result['error']}"
            return state
        # 统一格式
        state["mem_result"] = {
            "source_type": "memory",
            "content": result.get("content", "无记忆内容"),
            "metadata": result.get("metadata", {})
        }
    except Exception as e:
        state["error"] = f"记忆处理节点异常: {str(e)}"
    return state


# 节点：整合结果
def combine_results(state: MixAgentState) -> MixAgentState:
    state["combined_results"] = []
    if state.get("doc_result"):
        state["combined_results"].append(state["doc_result"])
    if state.get("img_result"):
        state["combined_results"].append(state["img_result"])
    if state.get("mem_result"):
        state["combined_results"].append(state["mem_result"])
    return state


# 创建混合智能体
def create_mix_agent():
    builder = StateGraph(MixAgentState)
    
    # 添加节点
    builder.add_node("process_document", process_document)
    builder.add_node("process_image", process_image)
    builder.add_node("process_memory", process_memory)
    builder.add_node("combine_results", combine_results)
    
    # 定义流程
    builder.add_edge(START, "process_document")
    builder.add_edge("process_document", "process_image")
    builder.add_edge("process_image", "process_memory")
    builder.add_edge("process_memory", "combine_results")
    builder.add_edge("combine_results", END)
    
    return builder.compile()


# 使用示例
if __name__ == "__main__":
    mix_agent = create_mix_agent()
    result = mix_agent.invoke({
        "doc_file_path": "test/孕前和孕期保健指南.doc",
        "img_file_path": "test/OIP.png",
        "chat_history": "test/chat.json",
        "persist_directory": "./test/vector_db"
    })
    
    if result["error"]:
        print(f"处理失败: {result['error']}")
    else:
        print("统一格式结果:")
        for item in result["combined_results"]:
            print(item)