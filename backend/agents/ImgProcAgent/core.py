"""
图片处理智能体
负责处理图片相关的任务（已移除imgproc_tool，依赖qwen_tool处理路径转Base64）
"""
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

import os
import yaml
from typing import TypedDict, Optional, Dict, Annotated

from langgraph.graph import StateGraph, END, START
from PIL import Image
from backend.agents.tools.tools import qwen_tool  # 仅保留qwen_tool


class ImgProcState(TypedDict):
    """
    图片处理智能体的状态结构（删除base64_content字段，无需提前存储编码结果）
    专注于图片路径、元数据与解析结果
    """
    file_path: Annotated[str, "图片本地路径（后端可访问）"]
    content: Optional[Annotated[str, "图片解析内容"]] = None
    metadata: Optional[Annotated[Dict, "图片元数据（格式、尺寸、大小等）"]] = None
    error: Optional[Annotated[str, "错误信息"]] = None


# ------------------------- 定义节点 ----------------------------
def extract_image_metadata(file_path: str) -> Dict:
    """辅助函数：提取图片元数据（格式、尺寸、文件大小等）"""
    try:
        with Image.open(file_path) as img:
            return {
                "format": img.format,       # 图片格式（如PNG/JPG）
                "size": img.size,           # 尺寸（宽, 高）
                "mode": img.mode,           # 色彩模式（如RGB）
                "file_size_bytes": os.path.getsize(file_path),  # 文件大小（字节）
                "file_path": file_path      # 原始路径
            }
    except Exception as e:
        return {"error": f"元数据提取失败: {str(e)}"}


def extract_image_metadata_node(state: ImgProcState) -> ImgProcState:
    """
    节点1：提取图片元数据与格式
    （原change_image_format节点简化，删除imgproc_tool调用，仅保留元数据提取）
    """
    try:
        # 校验图片路径是否存在
        if not os.path.exists(state["file_path"]):
            state["error"] = f"图片路径不存在：{state['file_path']}"
            return state

        # 提取元数据
        metadata = extract_image_metadata(state["file_path"])
        if "error" in metadata:
            state["error"] = f"元数据处理失败: {metadata['error']}"
            return state

        # 存储元数据与统一格式（小写，避免大小写不一致）
        state["metadata"] = metadata

    except Exception as e:
        state["error"] = f"元数据节点处理异常: {str(e)}"
    return state


def extract_image_content_node(state: ImgProcState) -> ImgProcState:
    """
    节点2：提取图片内容
    直接传递本地路径给qwen_tool（内部已通过QwenAIWrap处理路径→Base64编码）
    """
    # 前置校验：若有错误或无有效路径，直接返回
    if state.get("error") or not os.path.exists(state.get("file_path", "")):
        if not state.get("error"):
            state["error"] = "无效图片路径，无法提取内容"
        return state

    try:
        # 加载VL模型配置（确保使用支持图像理解的模型）
        with open("backend/config/model_settings.yaml", "r", encoding="utf-8") as f:
            model_settings = yaml.safe_load(f)
            vl_model_config = model_settings.get("VL_MODEL")
            if not vl_model_config:
                raise ValueError("配置文件中未找到VL_MODEL（视觉语言模型）配置")

        # 调用qwen_tool：直接传本地路径，无需提前编码
        qwen_result = qwen_tool.invoke({
            "input": "请详细描述图片内容：包括核心元素、文字信息（若有）、场景/类型（如报告/照片），禁止虚构未存在的信息，未识别到的内容标注为「未明确」",
            "img_path": state["file_path"],  # 关键：传递本地路径，qwen_tool内部转码
            "model_name": vl_model_config["llm_model"],
            "api_key": vl_model_config["api_key"],
            "base_url": vl_model_config["base_url"],
            "temperature": vl_model_config["temperature"]  # 低温度确保结果严谨
        })

        # 存储解析结果（兼容qwen_tool返回格式）
        state["content"] = qwen_result.get("content", "未提取到有效图片内容")

    except Exception as e:
        state["error"] = f"图片内容提取失败: {str(e)}"
    return state


# ------------------------- 定义流程 ----------------------------
def create_imgproc_agent():
    """
    创建图片处理智能体（简化版）
    流程：提取元数据→提取图片内容→结束
    """
    # 初始化状态图
    builder = StateGraph(ImgProcState)

    # 添加节点（重命名节点更贴合实际功能）
    builder.add_node("extract_metadata", extract_image_metadata_node)
    builder.add_node("extract_content", extract_image_content_node)

    # 定义流程链路
    builder.add_edge(START, "extract_metadata")          # 开始→提取元数据
    builder.add_edge("extract_metadata", "extract_content")  # 元数据→提取内容
    builder.add_edge("extract_content", END)             # 提取内容→结束

    return builder.compile()


# ------------------------- 使用示例 ----------------------------
if __name__ == "__main__":
    # 创建智能体实例
    img_agent = create_imgproc_agent()

    # 调用智能体（传入后端可访问的本地图片路径）
    result = img_agent.invoke({
        "file_path": "test/OIP.png"  # 替换为你的实际图片路径
    })

    # 输出结果（供后续智能体/接口使用的标准化格式）
    if result.get("error"):
        print(f"❌ 图片处理失败: {result['error']}")
    else:
        print("✅ 图片处理成功：")
        print({
            "source_type": "image",          # 来源类型（标识为图片）
            "content": result["content"],    # 图片解析内容
            "metadata": result['metadata']
        })