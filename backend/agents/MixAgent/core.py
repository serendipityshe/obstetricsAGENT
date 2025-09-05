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
from langchain.schema import AIMessage
from backend.agents.DocProcAgent.core import create_docproc_agent
from backend.agents.ImgProcAgent.core import create_imgproc_agent



class MixAgentState(TypedDict):
    """混合智能体状态"""
    # 输入参数（仅初始化时设置，后续节点不修改）
    input: Annotated[str, "用户输入"]
    doc_file_path: Optional[Annotated[str, "文档路径"]]
    img_file_path: Optional[Annotated[str, "图片路径"]]
    
    # 中间结果（各节点仅修改自身负责的键）
    doc_result: Optional[Annotated[dict, "文档处理结果"]]
    img_result: Optional[Annotated[dict, "图片处理结果"]]
    
    # 输出结果
    combined_results: Annotated[List[dict], "统一格式的结果列表"]
    error: Optional[Annotated[str, "错误信息"]]


# 节点：处理文档（修复：仅返回修改的状态键）
def process_document(state: MixAgentState) -> dict:  # 返回类型改为dict（仅增量状态）
    doc_path_str = state["doc_file_path"]
    if not doc_path_str:
        return {}  # 无修改，返回空字典
    
    doc_path = Path(doc_path_str)
    if not doc_path.exists():
        # 仅返回修改的error键
        return {"error": f"文档处理错误: 文件不存在（路径：{doc_path.absolute()}）"}
    if not doc_path.is_file():
        return {"error": f"文档处理错误: 不是有效文件（路径：{doc_path.absolute()}）"}
    
    try:
        doc_agent = create_docproc_agent()
        print(f"文档处理中：{doc_path.absolute()}")
        result = doc_agent.invoke({"input": state["input"], "file_path": str(doc_path.absolute())})
        
        if not isinstance(result, dict):
            return {"error": f"文档处理错误: DocProcAgent返回非字典格式（实际类型：{type(result).__name__}，内容：{str(result)}）"}
        
        if result.get('error'):
            return {"error": f"文档处理错误: {result['error']}"}
        
        # 提取AIMessage文本
        raw_content = result["content"]
        content = raw_content.content if isinstance(raw_content, AIMessage) else str(raw_content)
        
        # 仅返回修改的doc_result键
        return {
            "doc_result": {
                "source_type": "document",
                "file_type": result["file_type"],
                "content": content,
                "metadata": result["metadata"] or {}
            }
        }
    
    except Exception as e:
        error_stack = traceback.format_exc()
        error_msg = (
            f"文档处理节点异常:\n"
            f"异常信息：{str(e)}\n"
            f"异常堆栈：\n{error_stack}"
        )
        return {"error": error_msg}  # 仅返回error键


# 节点：处理图片（修复：仅返回修改的状态键）
def process_image(state: MixAgentState) -> dict:  # 返回类型改为dict（仅增量状态）
    img_path_str = state["img_file_path"]
    if not img_path_str:
        return {}  # 无修改，返回空字典
    
    img_path = Path(img_path_str)
    if not img_path.exists():
        return {"error": f"图片处理错误: 文件不存在（路径：{img_path.absolute()}）"}
    if not img_path.is_file():
        return {"error": f"图片处理错误: 不是有效文件（路径：{img_path.absolute()}）"}
    
    try:
        img_agent = create_imgproc_agent()
        print(f"图片处理中：{img_path.absolute()}")
        result = img_agent.invoke({"input": state["input"], "file_path": str(img_path.absolute())})
        
        if not isinstance(result, dict):
            return {"error": f"图片处理错误: ImgProcAgent返回非字典格式（实际类型：{type(result).__name__}）"}
        
        if result.get('error'):
            return {"error": f"图片处理错误: {result['error']}"}
        
        # 提取AIMessage文本
        raw_content = result["content"]
        content = raw_content.content if isinstance(raw_content, AIMessage) else str(raw_content)
        file_ext = img_path.suffix.lstrip(".").lower() if img_path.suffix else "unknown"
        
        # 仅返回修改的img_result键
        return {
            "img_result": {
                "source_type": "image",
                "file_type": file_ext,
                "content": content,
                "metadata": result["metadata"] or {}
            }
        }
    
    except Exception as e:
        error_stack = traceback.format_exc()
        error_msg = f"图片处理节点异常:\n{str(e)}\n{error_stack}"
        return {"error": error_msg}  # 仅返回error键


# 节点：整合结果（修复：仅返回修改的状态键）
def combine_results(state: MixAgentState) -> dict:  # 返回类型改为dict（仅增量状态）
    combined = []
    if state.get("doc_result"):
        combined.append(state["doc_result"])
    if state.get("img_result"):
        combined.append(state["img_result"])
    print(f"结果整合完成：共{len(combined)}个来源")
    # 仅返回修改的combined_results键
    return {"combined_results": combined}


# 创建混合智能体（逻辑不变）
def mix_agent():
    builder = StateGraph(MixAgentState)
    
    # 添加节点
    builder.add_node("process_document", process_document)
    builder.add_node("process_image", process_image)
    builder.add_node("combine_results", combine_results)
    
    # 定义流程（并发执行文档/图片处理，最后整合）
    builder.add_edge(START, "process_document")
    builder.add_edge(START, "process_image")
    builder.add_edge("process_document", "combine_results")
    builder.add_edge("process_image", "combine_results")
    builder.add_edge("combine_results", END)
    
    return builder.compile()


# 使用示例（逻辑不变）
if __name__ == "__main__":
    script_dir = Path(__file__).parent
    test_dir = script_dir.parent.parent.parent / "test"
    
    input_params = {
        "input": "孕期保健",
        "doc_file_path": str(test_dir / "孕前和孕期保健指南.doc"),
        "img_file_path": str(test_dir / "OIP.png"),
    }
    
    print("=== 输入参数 ===")
    for key, value in input_params.items():
        print(f"{key}: {value}")
    print("=" * 50)
    
    mix_agent = mix_agent()
    result = mix_agent.invoke(input_params)
    
    if result.get('error'):
        print(f"\n=== 处理失败 ===")
        print(result['error'])
    else:
        print(f"\n=== 处理成功 ===")
        print("统一格式结果:")
        for idx, item in enumerate(result["combined_results"], 1):
            content = str(item['content']).strip()
            print(f"\n{idx}. 来源类型：{item['source_type']}")
            print(f"   文件类型：{item.get('file_type', '无')}")
            print(f"   元数据：{item['metadata']}")
            if len(content) > 200:
                print(f"   内容预览：{content[:200]}...")
            else:
                print(f"   内容：{content}")
    