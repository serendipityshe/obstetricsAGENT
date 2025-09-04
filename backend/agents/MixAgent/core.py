"""
混合智能体
负责对齐DocProcAgent, ImgProcAgent, MeMAgent的输出格式，整合成统一结构供检索智能体使用
"""
import sys
import traceback
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from typing import TypedDict, Optional, List, Annotated
from langgraph.graph import StateGraph, END, START
# 新增：导入AIMessage用于类型判断（需确保langchain版本正确）
from langchain.schema import AIMessage
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


# 节点：处理文档（修复：提取AIMessage的文本内容）
def process_document(state: MixAgentState) -> MixAgentState:
    doc_path_str = state["doc_file_path"]
    if not doc_path_str:
        return state
    
    doc_path = Path(doc_path_str)
    if not doc_path.exists():
        state["error"] = f"文档处理错误: 文件不存在（路径：{doc_path.absolute()}）"
        return state
    if not doc_path.is_file():
        state["error"] = f"文档处理错误: 不是有效文件（路径：{doc_path.absolute()}）"
        return state
    
    try:
        doc_agent = create_docproc_agent()
        print(f"文档处理中：{doc_path.absolute()}")
        result = doc_agent.invoke({"file_path": str(doc_path.absolute())})
        
        if not isinstance(result, dict):
            state["error"] = f"文档处理错误: DocProcAgent返回非字典格式（实际类型：{type(result).__name__}，内容：{str(result)}）"
            return state
        
        if result.get('error'):
            state["error"] = f"文档处理错误: {result['error']}"
            return state
        
        # 修复核心：判断是否为AIMessage，提取其content文本（关键修改）
        raw_content = result["content"]
        content = raw_content.content if isinstance(raw_content, AIMessage) else str(raw_content)
        
        state["doc_result"] = {
            "source_type": "document",
            "file_type": result["file_type"],
            "content": content,  # 使用提取后的文本
            "metadata": result["metadata"] or {}
        }
        print(f"文档处理成功：{doc_path.name}")
    
    except Exception as e:
        error_stack = traceback.format_exc()
        error_msg = (
            f"文档处理节点异常:\n"
            f"异常信息：{str(e)}\n"
            f"异常堆栈：\n{error_stack}"
        )
        state["error"] = error_msg
        print(error_msg)
    return state


# 节点：处理图片（修复：提取AIMessage的文本内容）
def process_image(state: MixAgentState) -> MixAgentState:
    img_path_str = state["img_file_path"]
    if not img_path_str:
        return state
    
    img_path = Path(img_path_str)
    if not img_path.exists():
        state["error"] = f"图片处理错误: 文件不存在（路径：{img_path.absolute()}）"
        return state
    if not img_path.is_file():
        state["error"] = f"图片处理错误: 不是有效文件（路径：{img_path.absolute()}）"
        return state
    
    try:
        img_agent = create_imgproc_agent()
        print(f"图片处理中：{img_path.absolute()}")
        result = img_agent.invoke({"file_path": str(img_path.absolute())})
        
        if not isinstance(result, dict):
            state["error"] = f"图片处理错误: ImgProcAgent返回非字典格式（实际类型：{type(result).__name__}）"
            return state
        
        if result.get('error'):
            state["error"] = f"图片处理错误: {result['error']}"
            return state
        
        # 修复核心：提取AIMessage文本（关键修改）
        raw_content = result["content"]
        content = raw_content.content if isinstance(raw_content, AIMessage) else str(raw_content)
        file_ext = img_path.suffix.lstrip(".").lower() if img_path.suffix else "unknown"
        
        state["img_result"] = {
            "source_type": "image",
            "file_type": file_ext,
            "content": content,  # 使用提取后的文本
            "metadata": result["metadata"] or {}
        }
        print(f"图片处理成功：{img_path.name}")
    
    except Exception as e:
        error_stack = traceback.format_exc()
        error_msg = f"图片处理节点异常:\n{str(e)}\n{error_stack}"
        state["error"] = error_msg
        print(error_msg)
    return state


# 节点：处理记忆（修复：提取AIMessage的文本内容）
def process_memory(state: MixAgentState) -> MixAgentState:
    try:
        mem_agent = create_mem_agent()
        print(f"记忆处理中：存储目录={state['persist_directory']}")
        result = mem_agent.invoke({
            "chat_history": state["chat_history"],
            "persist_directory": state["persist_directory"]
        })
        
        if not isinstance(result, dict):
            state["error"] = f"记忆处理错误: MeMAgent返回非字典格式（实际类型：{type(result).__name__}）"
            return state
        
        if result.get("error"):
            state["error"] = f"记忆处理错误: {result['error']}"
            return state
        
        # 修复核心：提取AIMessage文本（关键修改）
        raw_content = result.get("content", "无记忆内容")
        content = raw_content.content if isinstance(raw_content, AIMessage) else str(raw_content)
        
        state["mem_result"] = {
            "source_type": "memory",
            "content": content,  # 使用提取后的文本
            "metadata": result.get("metadata", {})
        }
        print("记忆处理成功")
    
    except Exception as e:
        error_stack = traceback.format_exc()
        error_msg = f"记忆处理节点异常:\n{str(e)}\n{error_stack}"
        state["error"] = error_msg
        print(error_msg)
    return state


# 节点：整合结果（保持原有逻辑）
def combine_results(state: MixAgentState) -> MixAgentState:
    state["combined_results"] = []
    if state.get("doc_result"):
        state["combined_results"].append(state["doc_result"])
    if state.get("img_result"):
        state["combined_results"].append(state["img_result"])
    if state.get("mem_result"):
        state["combined_results"].append(state["mem_result"])
    print(f"结果整合完成：共{len(state['combined_results'])}个来源")
    return state


# 创建混合智能体（保持原有逻辑）
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


# 使用示例（优化：增强打印兼容性）
if __name__ == "__main__":
    script_dir = Path(__file__).parent
    test_dir = script_dir.parent.parent.parent / "test"
    
    input_params = {
        "doc_file_path": str(test_dir / "孕前和孕期保健指南.doc"),
        "img_file_path": str(test_dir / "OIP.png"),
        "chat_history": str(test_dir / "chat.json"),
        "persist_directory": str(test_dir / "vector_db")
    }
    
    print("=== 输入参数 ===")
    for key, value in input_params.items():
        print(f"{key}: {value}")
    print("=" * 50)
    
    mix_agent = create_mix_agent()
    result = mix_agent.invoke(input_params)
    
    if result.get('error'):
        print(f"\n=== 处理失败 ===")
        print(result['error'])
    else:
        print(f"\n=== 处理成功 ===")
        print("统一格式结果:")
        for idx, item in enumerate(result["combined_results"], 1):
            # 优化：确保content是字符串（双重保险）
            content = str(item['content']).strip()
            print(f"\n{idx}. 来源类型：{item['source_type']}")
            print(f"   文件类型：{item.get('file_type', '无')}")
            print(f"   元数据：{item['metadata']}")
            # 修复切片报错：基于字符串长度判断
            if len(content) > 200:
                print(f"   内容预览：{content[:200]}...")
            else:
                print(f"   内容：{content}")
    