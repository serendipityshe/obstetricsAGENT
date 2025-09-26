"""
向量化对话历史检索模块
基于相关性检索历史对话片段，而非全量加载
"""

import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from typing import TypedDict, Optional, Dict, Annotated, List
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class RetrievalMemoryState(TypedDict):
    """检索式记忆状态定义"""
    maternal_id: Annotated[int, '孕妇ID']
    chat_id: Annotated[str, '对话ID']
    current_input: Annotated[str, '当前用户输入']

    # 输出字段
    relevant_history: Annotated[Optional[str], '相关历史对话片段']
    history_summary: Annotated[Optional[str], '历史摘要信息']
    error: Annotated[Optional[str], '错误信息']

def retrieve_relevant_history(state: RetrievalMemoryState) -> RetrievalMemoryState:
    """基于当前输入检索相关的历史对话片段"""
    try:
        maternal_id = state.get("maternal_id")
        chat_id = state.get("chat_id")
        current_input = state.get("current_input", "")

        if not current_input:
            state["relevant_history"] = ""
            state["history_summary"] = "无当前输入，跳过历史检索"
            return state

        # 1. 尝试从向量数据库检索相关历史
        vector_db_path = f"/root/project2/data/vector_store/chat_{chat_id}_maternal_{maternal_id}"
        relevant_chunks = _search_vector_memory(current_input, vector_db_path)

        # 2. 如果向量数据库没有内容，回退到最近对话检索
        if not relevant_chunks:
            relevant_chunks = _fallback_recent_history(maternal_id, chat_id, max_turns=2)

        # 3. 构建相关历史文本
        if relevant_chunks:
            # 限制总长度不超过1500字符
            total_length = 0
            selected_chunks = []

            for chunk in relevant_chunks:
                chunk_text = chunk.get("content", "")
                if total_length + len(chunk_text) <= 1500:
                    selected_chunks.append(chunk_text)
                    total_length += len(chunk_text)
                else:
                    # 如果剩余空间足够，截断添加
                    remaining = 1500 - total_length
                    if remaining > 100:  # 至少保留100字符才有意义
                        selected_chunks.append(chunk_text[:remaining] + "...[截断]")
                    break

            relevant_history = "\n---\n".join(selected_chunks)
            history_summary = f"检索到{len(selected_chunks)}个相关历史片段，总长度{len(relevant_history)}字符"
        else:
            relevant_history = ""
            history_summary = "未找到相关历史对话"

        state["relevant_history"] = relevant_history
        state["history_summary"] = history_summary

        logger.info(f"历史检索完成: {history_summary}")

    except Exception as e:
        error_msg = f"历史检索失败: {str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["relevant_history"] = ""
        state["history_summary"] = "历史检索失败"

    return state

def _search_vector_memory(query: str, vector_db_path: str, top_k: int = 3) -> List[Dict]:
    """从向量数据库搜索相关记忆片段"""
    try:
        if not os.path.exists(vector_db_path):
            return []

        # 使用现有的检索工具
        from backend.agents import create_retr_agent
        from backend.agents.RetrAgent.core import RetrAgentState

        retr_agent = create_retr_agent()
        retr_input: RetrAgentState = {
            "input": query,
            "vector_db_professor": "",  # 不使用专家库
            "vector_db_pregnant": vector_db_path,  # 使用对话历史向量库
        }

        result = retr_agent.invoke(retr_input)
        output_data = result.get("output", {})

        if isinstance(output_data, dict):
            pregnant_results = output_data.get("孕妇知识库", [])
            # 转换格式
            return [{"content": item.get("content", ""), "metadata": item.get("source", "")}
                   for item in pregnant_results[:top_k] if item.get("content")]

        return []

    except Exception as e:
        logger.warning(f"向量检索失败，将使用备用方案: {e}")
        return []

def _fallback_recent_history(maternal_id: int, chat_id: str, max_turns: int = 2) -> List[Dict]:
    """备用方案：获取最近的对话记录"""
    try:
        from backend.api.v1.services.maternal_service import MaternalService
        maternal_service = MaternalService()

        # 获取对话记录文件路径
        json_file_path = maternal_service.get_dialogue_content_by_chat_id(chat_id)
        if not isinstance(json_file_path, str) or not os.path.exists(json_file_path):
            return []

        # 读取历史对话数据
        with open(json_file_path, 'r', encoding='utf-8') as f:
            history_data = json.load(f)

        if not isinstance(history_data, list):
            history_data = [history_data] if history_data else []

        # 获取最近的对话片段
        recent_conversations = []
        conversation_count = 0

        # 从最新记录开始遍历
        for item in reversed(history_data):
            if conversation_count >= max_turns:
                break

            if isinstance(item, dict) and "data" in item:
                messages = item["data"].get("messages", [])

                # 构建对话片段
                conversation_text = ""
                for msg in messages:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        role_name = "用户" if msg["role"] == "user" else "助手"

                        # 提取文本内容
                        text_content = ""
                        if isinstance(msg["content"], list):
                            for content_item in msg["content"]:
                                if isinstance(content_item, dict) and content_item.get("type") == "text":
                                    text_content += content_item.get("text", "")
                        else:
                            text_content = str(msg["content"])

                        if text_content.strip():
                            conversation_text += f"{role_name}: {text_content.strip()}\n"

                if conversation_text.strip():
                    recent_conversations.append({
                        "content": conversation_text.strip(),
                        "metadata": f"最近对话_{conversation_count + 1}"
                    })
                    conversation_count += 1

        return recent_conversations

    except Exception as e:
        logger.error(f"备用历史检索失败: {e}")
        return []

def create_retrieval_memory_function():
    """创建检索式记忆处理函数"""
    def process_retrieval_memory(maternal_id: int, chat_id: str, current_input: str) -> Dict:
        """处理检索式记忆的便捷函数"""
        state: RetrievalMemoryState = {
            "maternal_id": maternal_id,
            "chat_id": chat_id,
            "current_input": current_input
        }

        result_state = retrieve_relevant_history(state)

        return {
            "relevant_history": result_state.get("relevant_history", ""),
            "history_summary": result_state.get("history_summary", ""),
            "error": result_state.get("error")
        }

    return process_retrieval_memory

if __name__ == "__main__":
    # 测试检索式记忆
    process_memory = create_retrieval_memory_function()

    test_result = process_memory(
        maternal_id=3,
        chat_id="chat_3_pregnant_mother_967c973a-2e0b-4744-b7df-75b9d0d52634",
        current_input="羊水过多怎么办"
    )

    print("检索式记忆测试结果：")
    for key, value in test_result.items():
        if value and len(str(value)) > 200:
            print(f"{key}: {str(value)[:200]}...")
        else:
            print(f"{key}: {value}")