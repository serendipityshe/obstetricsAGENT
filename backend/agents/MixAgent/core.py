"""
混合智能体
负责对齐DocProcAgent,ImgProcAgent,MemAgent的输出格式，整合格式之后进行供后续检索智能体使用
"""

from typing import TypedDict, Optional, Dict, Annotated
from langgraph.graph import StateGraph, END, START
from backend.agents.DocProcAgent.core import create_docproc_agent
from backend.agents.ImgProcAgent.core import create_imgproc_agent
from backend.agents.MemAgent.core import create_mem_agent


class MixAgentState(TypedDict):
    """
    混合智能体状态
    """
    chat_history: Annotated[list, "聊天历史"]
    persist_directory: Annotated[str, "长期记忆存储目录"]
    error: Annotated[Optional[str], "错误信息"]


