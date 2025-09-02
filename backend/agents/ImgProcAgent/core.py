"""
图片处理智能体
负责处理图片相关的任务
"""

from typing import TypedDict, Optional, Dict, Annotated
from langgraph.graph import StateGraph, END, START
from backend.agents.tools.tools import imgproc_tool
from backend.agents.tools.tools import qwen_tool
from PIL import Image
import os


class ImgProcState(TypedDict):
    """
    图片处理智能体的状态结构
    专注于图片解析结果.
    """
    file_path: Annotated[str, "图片路径"]
    content: Optional[Annotated[str, "图片解析内容"]]
    metadata: Optional[Annotated[str, '图片元数据']]
    file_type: Optional[Annotated[str, '图片格式']]
    error: Optional[Annotated[str, "错误信息"]]

#-------------------------定义节点----------------------------
def extract_image_metadata(file_path: str) -> Dict:
    try:
        with Image.open(file_path) as img:
            return {
                "format": img.format,
                "size": img.size,
                "mode": img.mode,
                "file_size": os.path.getsize(file_path),
                "file_path": file_path
            }
    except Exception as e:
        return {"error": f"提取元数据失败: {str(e)}"}


def change_image_format(state: ImgProcState) -> ImgProcState:
    """
    检测图片格式节点
    """
    try:
        with Image.open(state["file_path"]) as img:
            metadata =  {
                "format": img.format,
                "size": img.size,
                "mode": img.mode,
                "file_size": os.path.getsize(state["file_path"]),
                "file_path": state["file_path"]
            }
            state["metadata"] = metadata
        img_path = imgproc_tool.invoke(state["file_path"])
        state["file_path"] = img_path
    except Exception as e:
        state["error"] = f"图片格式或者元素据提取/转换失败: {str(e)}"
    return state

def extract_image_content(state: ImgProcState) -> ImgProcState:
    """
    提取图片内容节点
    """
    try:
        img_content = qwen_tool.invoke(
            state["file_path"])
        state["content"] = img_content
    except Exception as e:
        state["error"] = f"图片内容提取失败: {str(e)}"
    return state

#--------------------------------定义流程----------------------------
def create_imgproc_agent():
    """
    创建图片处理智能体
    输出可直接作为后续融合流程的图片上下文来源
    """
    builder = StateGraph(ImgProcState)

    #添加节点
    builder.add_node("change_image_format", change_image_format)
    builder.add_node("extract_image_content", extract_image_content)

    #添加边
    builder.add_edge(START, "change_image_format")
    builder.add_edge("change_image_format", "extract_image_content")
    builder.add_edge("extract_image_content", END)

    return builder.compile()

#使用示例
if __name__ == "__main__":
    img_agent = create_imgproc_agent()

    result = img_agent.invoke({
        "file_path": "medical_record.png"
    })
    # 输出结果（供后续智能体使用的格式）
    if result["error"]:
        print(f"图片处理失败: {result['error']}")
    else:
        print({
            "source_type": "image",
            "content": result["content"],
            "metadata": result["metadata"]
        })