"""
混合智能体
负责对齐DocProcAgent, ImgProcAgent, MeMAgent的输出格式，整合成统一结构供检索智能体使用
"""
import sys
import traceback  # 新增：用于打印详细异常堆栈
from pathlib import Path  # 新增：用于文件路径校验
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


# 节点：处理文档（核心优化：路径校验+详细异常+结果类型校验）
def process_document(state: MixAgentState) -> MixAgentState:
    doc_path_str = state["doc_file_path"]
    if not doc_path_str:
        return state
    
    # 优化1：校验文档路径是否存在且为有效文件
    doc_path = Path(doc_path_str)
    if not doc_path.exists():
        state["error"] = f"文档处理错误: 文件不存在（路径：{doc_path.absolute()}）"
        return state
    if not doc_path.is_file():
        state["error"] = f"文档处理错误: 不是有效文件（路径：{doc_path.absolute()}）"
        return state
    
    try:
        # 优化2：确认DocProcAgent初始化（若需参数需补充，如persist_directory）
        doc_agent = create_docproc_agent()
        # 优化3：打印调试信息，确认传入参数
        print(f"文档处理中：{doc_path.absolute()}")
        result = doc_agent.invoke({"file_path": str(doc_path.absolute())})  # 传入绝对路径
        
        # 优化4：校验Agent返回结果是否为字典（避免非预期格式）
        if not isinstance(result, dict):
            state["error"] = f"文档处理错误: DocProcAgent返回非字典格式（实际类型：{type(result).__name__}，内容：{str(result)}）"
            return state
        
        # 原有逻辑：检查Agent返回的错误
        if result.get('error'):
            state["error"] = f"文档处理错误: {result['error']}"
            return state
        
        # 统一格式（保持原有逻辑）
        state["doc_result"] = {
            "source_type": "document",
            "file_type": result["file_type"],
            "content": result["content"],
            "metadata": result["metadata"] or {}
        }
        print(f"文档处理成功：{doc_path.name}")  # 调试信息
    
    # 优化5：捕获异常并打印完整堆栈（关键：定位具体错误行）
    except Exception as e:
        error_stack = traceback.format_exc()  # 获取完整异常堆栈
        error_msg = (
            f"文档处理节点异常:\n"
            f"异常信息：{str(e)}\n"
            f"异常堆栈：\n{error_stack}"
        )
        state["error"] = error_msg
        print(error_msg)  # 打印到控制台便于调试
    return state


# 节点：处理图片（新增：路径校验+异常堆栈优化）
def process_image(state: MixAgentState) -> MixAgentState:
    img_path_str = state["img_file_path"]
    if not img_path_str:
        return state
    
    # 新增：校验图片路径
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
        
        # 新增：校验返回结果格式
        if not isinstance(result, dict):
            state["error"] = f"图片处理错误: ImgProcAgent返回非字典格式（实际类型：{type(result).__name__}）"
            return state
        
        if result.get('error'):
            state["error"] = f"图片处理错误: {result['error']}"
            return state
        
        # 统一格式（保持原有逻辑，优化：处理无后缀名的情况）
        file_ext = img_path.suffix.lstrip(".").lower() if img_path.suffix else "unknown"
        state["img_result"] = {
            "source_type": "image",
            "file_type": file_ext,
            "content": result["content"],
            "metadata": result["metadata"] or {}
        }
        print(f"图片处理成功：{img_path.name}")
    
    # 新增：详细异常堆栈
    except Exception as e:
        error_stack = traceback.format_exc()
        error_msg = f"图片处理节点异常:\n{str(e)}\n{error_stack}"
        state["error"] = error_msg
        print(error_msg)
    return state


# 节点：处理记忆（新增：异常堆栈优化）
def process_memory(state: MixAgentState) -> MixAgentState:
    try:
        mem_agent = create_mem_agent()
        print(f"记忆处理中：存储目录={state['persist_directory']}")
        result = mem_agent.invoke({
            "chat_history": state["chat_history"],
            "persist_directory": state["persist_directory"]
        })
        
        # 新增：校验返回结果格式
        if not isinstance(result, dict):
            state["error"] = f"记忆处理错误: MeMAgent返回非字典格式（实际类型：{type(result).__name__}）"
            return state
        
        if result.get("error"):
            state["error"] = f"记忆处理错误: {result['error']}"
            return state
        
        # 统一格式（保持原有逻辑）
        state["mem_result"] = {
            "source_type": "memory",
            "content": result.get("content", "无记忆内容"),
            "metadata": result.get("metadata", {})
        }
        print("记忆处理成功")
    
    # 新增：详细异常堆栈
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
    
    # 定义流程（保持原有逻辑，若需并行可调整，但当前串行不影响功能）
    builder.add_edge(START, "process_document")
    builder.add_edge("process_document", "process_image")
    builder.add_edge("process_image", "process_memory")
    builder.add_edge("process_memory", "combine_results")
    builder.add_edge("combine_results", END)
    
    return builder.compile()


# 使用示例（优化：使用绝对路径，避免相对路径问题）
if __name__ == "__main__":
    # 优化：基于脚本位置构建绝对路径（避免运行目录影响）
    script_dir = Path(__file__).parent  # 当前脚本所在目录（MixAgent/core.py）
    test_dir = script_dir.parent.parent.parent / "test"  # 定位到project2/test目录
    
    # 构造绝对路径参数
    input_params = {
        "doc_file_path": str(test_dir / "孕前和孕期保健指南.doc"),
        "img_file_path": str(test_dir / "OIP.png"),
        "chat_history": str(test_dir / "chat.json"),  # 假设chat_history是文件路径（需确认MeMAgent预期格式）
        "persist_directory": str(test_dir / "vector_db")
    }
    
    # 打印输入参数，确认路径正确性
    print("=== 输入参数 ===")
    for key, value in input_params.items():
        print(f"{key}: {value}")
    print("=" * 50)
    
    # 执行智能体
    mix_agent = create_mix_agent()
    result = mix_agent.invoke(input_params)
    
    # 输出结果（保持原有逻辑）
    if result.get('error'):
        print(f"\n=== 处理失败 ===")
        print(result['error'])
    else:
        print(f"\n=== 处理成功 ===")
        print("统一格式结果:")
        for idx, item in enumerate(result["combined_results"], 1):
            print(f"\n{idx}. 来源类型：{item['source_type']}")
            print(f"   文件类型：{item.get('file_type', '无')}")
            print(f"   元数据：{item['metadata']}")
            print(f"   内容预览：{item['content'][:200]}..." if len(str(item['content'])) > 200 else f"   内容：{item['content']}")
    