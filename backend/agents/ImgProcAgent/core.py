"""
图片处理智能体
负责处理图片相关的任务
"""

import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from typing import TypedDict, Optional, Dict, Annotated
from langgraph.graph import StateGraph, END, START
from backend.agents.tools.tools import imgproc_tool
from backend.agents.tools.tools import qwen_tool
from PIL import Image
import os
import yaml




class ImgProcState(TypedDict):
    """
    图片处理智能体的状态结构
    专注于图片解析结果.
    """
    file_path: Annotated[str, "图片路径"]
    base64_content: Annotated[str, "图片base64编码"]
    content: Optional[Annotated[str, "图片解析内容"]]
    metadata: Optional[Annotated[Dict, '图片元数据']]
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
        metadata = extract_image_metadata(state["file_path"])
        if "error" in metadata:
            state["error"] = f"图片元数据提取失败: {metadata['error']}"
            return state
        state['metadata'] = metadata
        state['file_type'] = metadata["format"].lower()

        imgproc_result = imgproc_tool.invoke({"file_path": state["file_path"]})
        if imgproc_result['status'] != 'success':
            state["error"] = f"图片格式转换失败: {imgproc_result['error']}"
            return state
        state["base64_content"] = imgproc_result["content"]
    except Exception as e:
        state["error"] = f"图片格式或者元素据提取/转换失败: {str(e)}"
    return state

def extract_image_content(state: ImgProcState) -> ImgProcState:
    """
    提取图片内容节点
    """
    if state["error"] or not state.get("base64_content"):
        return state
    try:

        with open('backend/config/model_settings.yaml', 'r', encoding= 'utf-8') as f:
            model_settings = yaml.safe_load(f)
            default_model = model_settings['VL_MODEL']
        model_name = default_model['llm_model']
        api_key = default_model['api_key']
        base_url = default_model['base_url']
        temperature = default_model['temperature']

        image_query = f"data:image/{state['file_type']};base64,{state['base64_content']}"
        qwen_result = qwen_tool.invoke({
            "input": image_query,
            "model_name": model_name,
            "api_key": api_key,
            "base_url": base_url,
            "temperature": temperature
        })
        state["content"] = qwen_result.get("content", "未提取到图片内容")
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
        "img_file_path": "test/OIP.png"
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