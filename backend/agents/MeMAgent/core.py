import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from typing import TypedDict, Optional, Dict, Annotated, List
from langgraph.graph import StateGraph, END, START
from backend.agents.tools.tools import save_memory
from datetime import datetime
import json
import os
import logging

from backend.dataset.db.models import MaternalDialogue
from backend.dataset.db.service import get_session, get_db_engine

logger = logging.getLogger(__name__)


class MeMStateRequired(TypedDict):
    """长期记忆智能体状态定义 - 必需字段"""
    maternal_id: Annotated[int, '孕妇ID']
    chat_id: Annotated[str, '对话ID']

class MeMState(MeMStateRequired, total=False):
    """长期记忆智能体状态定义 - 完整状态（包含可选字段）"""
    chat_history: Annotated[Optional[List[Dict[str, str]]], '对话历史（结构化）']
    chat_history_text: Annotated[Optional[str], '对话历史（文本形式）']
    compressed_memory: Annotated[Optional[str], '压缩后的记忆']
    memory_summary: Annotated[Optional[str], '记忆摘要']
    
    # 配置参数
    max_turns_in_memory: Annotated[Optional[int], '内存中保留的最大轮数']
    persist_directory: Annotated[Optional[str], '向量数据库路径']
    
    # 输出字段
    error: Optional[Annotated[str, '错误信息']]
    content: Optional[Annotated[str, '处理结果信息']]
    metadata: Optional[Annotated[Dict, '附加元数据']]


def load_chat_history_node(state: MeMState) -> MeMState:
    """对话历史加载节点 - 从文件系统加载历史对话记录"""
    try:
        from backend.api.v1.services.maternal_service import MaternalService
        maternal_service = MaternalService()
        
        chat_id = state.get("chat_id")
        if not chat_id:
            logger.warning("chat_id为空，无法加载对话历史")
            state["chat_history"] = []
            state["chat_history_text"] = ""
            return state
        
        # 获取对话记录文件路径
        json_file_path = maternal_service.get_dialogue_content_by_chat_id(chat_id)
        if not isinstance(json_file_path, str) or not os.path.exists(json_file_path):
            logger.info(f"对话文件不存在或为新对话: {chat_id}")
            state["chat_history"] = []
            state["chat_history_text"] = ""
            return state
        
        # 读取历史对话数据
        with open(json_file_path, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
            
        # 处理历史数据格式
        if not isinstance(history_data, list):
            history_data = [history_data] if history_data else []
        
        # 提取对话历史
        chat_history = []
        for item in history_data:
            if isinstance(item, dict) and "data" in item:
                messages = item["data"].get("messages", [])
                for msg in messages:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        # 提取文本内容
                        text_content = ""
                        if isinstance(msg["content"], list):
                            for content_item in msg["content"]:
                                if isinstance(content_item, dict) and content_item.get("type") == "text":
                                    text_content += content_item.get("text", "")
                        else:
                            text_content = str(msg["content"])
                        
                        if text_content.strip():
                            chat_history.append({
                                "role": msg["role"],
                                "content": text_content.strip(),
                                "timestamp": msg.get("timestamp", "")
                            })
        
        # 转换为文本格式
        chat_history_text = ""
        if chat_history:
            history_lines = []
            for msg in chat_history:
                role_name = "用户" if msg["role"] == "user" else "助手"
                history_lines.append(f"{role_name}: {msg['content']}")
            chat_history_text = "\n".join(history_lines)
        
        state["chat_history"] = chat_history
        state["chat_history_text"] = chat_history_text
        logger.info(f"成功加载对话历史: {len(chat_history)}条记录")
        
    except Exception as e:
        error_msg = f"加载对话历史失败: {str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["chat_history"] = []
        state["chat_history_text"] = ""
    
    return state

def memory_management_node(state: MeMState) -> MeMState:
    """记忆管理节点 - 根据轮数决定保留在内存中还是存储到向量数据库"""
    try:
        chat_history = state.get("chat_history", [])
        max_turns = state.get("max_turns_in_memory") or 5  # 修复：处理None值
        maternal_id = state.get("maternal_id")
        chat_id = state.get("chat_id")
        
        if not chat_history:
            state["compressed_memory"] = ""
            state["memory_summary"] = "无对话历史"
            return state
        
        # 计算对话轮数（用户+助手=1轮）
        user_messages = [msg for msg in chat_history if msg["role"] == "user"]
        total_turns = len(user_messages)
        
        logger.info(f"当前对话轮数: {total_turns}, 最大内存轮数: {max_turns}")
        
        if total_turns <= max_turns:  # 现在max_turns不会是None了
            # 轮数较少，保留在内存中
            compressed_memory = state.get("chat_history_text", "")
            memory_summary = f"对话轮数({total_turns})未超过阈值({max_turns})，保留在内存中"
            
        else:
            # 轮数较多，需要压缩和存储
            # 保留最近的对话轮数
            recent_messages = []
            recent_user_count = 0
            
            # 从后往前遍历，保留最近的max_turns轮对话
            for msg in reversed(chat_history):
                if msg["role"] == "user":
                    if recent_user_count >= max_turns:  # 现在max_turns不会是None了
                        break
                    recent_user_count += 1
                recent_messages.insert(0, msg)
            
            # 构建最近对话的文本形式
            recent_lines = []
            for msg in recent_messages:
                role_name = "用户" if msg["role"] == "user" else "助手"
                recent_lines.append(f"{role_name}: {msg['content']}")
            compressed_memory = "\n".join(recent_lines)
            
            # 将较早的对话存储到向量数据库
            older_messages = [msg for msg in chat_history if msg not in recent_messages]
            if older_messages:
                save_result = _save_to_vector_db(older_messages, maternal_id, chat_id)
                if save_result["success"]:
                    memory_summary = f"已将{len(older_messages)}条早期记录存储到向量数据库，保留最近{max_turns}轮对话在内存中"
                else:
                    memory_summary = f"向量数据库存储失败: {save_result['error']}"
            else:
                memory_summary = f"保留最近{max_turns}轮对话在内存中"
        
        state["compressed_memory"] = compressed_memory
        state["memory_summary"] = memory_summary
        state["content"] = f"记忆管理完成: {memory_summary}"
        
        logger.info(f"记忆管理完成: {memory_summary}")
        
    except Exception as e:
        error_msg = f"记忆管理失败: {str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["compressed_memory"] = state.get("chat_history_text", "")
        state["memory_summary"] = "记忆管理失败，使用原始记录"
    
    return state

def _save_to_vector_db(messages: List[Dict], maternal_id: int, chat_id: str) -> Dict:
    """将对话记录保存到向量数据库并更新数据库记录"""
    try:
        # 创建临时文件存储对话记录
        temp_dir = Path(f"/tmp/chat_history_{maternal_id}")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / f"{chat_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # 构建对话记录摘要（用于向量化存储）
        conversation_summary = {
            "chat_id": chat_id,
            "maternal_id": maternal_id,
            "timestamp": datetime.now().isoformat(),
            "conversation_summary": "",
            "key_topics": [],
            "messages": messages
        }
        
        # 提取关键信息
        key_content = []
        for msg in messages:
            content = msg.get("content", "")
            if len(content) > 20:  # 只保留有意义的内容
                if any(keyword in content for keyword in ["症状", "检查", "建议", "诊断", "治疗", "药物", "孕期", "胎儿"]):
                    key_content.append(content)
        
        conversation_summary["conversation_summary"] = ". ".join(key_content[:5])  # 最多5个关键内容
        conversation_summary["key_topics"] = list(set([
            word for content in key_content for word in ["症状", "检查", "建议", "诊断", "治疗", "药物", "孕期", "胎儿"] 
            if word in content
        ]))
        
        # 保存到临时文件
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(conversation_summary, f, ensure_ascii=False, indent=2)
        
        # 使用现有的save_memory工具存储到向量数据库
        vector_db_path = f"/root/project2/data/vector_store/chat_{chat_id}_maternal_{maternal_id}"
        result = save_memory.invoke({
            "chat_history": str(temp_file),
            "persist_directory": vector_db_path
        })
        
        # 更新数据库中的向量存储路径
        try:
            from backend.api.v1.services.maternal_service import MaternalService
            maternal_service = MaternalService()
            
            # 更新对话记录中的向量存储路径
            maternal_service.dataset_service.update_dialogue(
                maternal_id=maternal_id,
                chat_id=chat_id,
                vector_store_path=vector_db_path
            )
            logger.info(f"已更新数据库中chat_id={chat_id}的向量存储路径: {vector_db_path}")
                
        except Exception as db_error:
            logger.warning(f"数据库路径更新失败，但向量存储成功: {db_error}")
        
        # 清理临时文件
        if temp_file.exists():
            temp_file.unlink()
        
        return {"success": True, "vector_path": vector_db_path}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def create_enhanced_mem_agent():
    """创建增强版长期记忆智能体"""
    builder = StateGraph(MeMState)
    
    # 添加节点
    builder.add_node("load_history", load_chat_history_node)
    builder.add_node("memory_management", memory_management_node)
    
    # 构建流程：加载历史 -> 记忆管理
    builder.add_edge(START, "load_history")
    builder.add_edge("load_history", "memory_management")
    builder.add_edge("memory_management", END)
    
    return builder.compile()
def save_memory_node(state: MeMState) -> MeMState:
    """长期记忆智能体节点：保存对话记录到向量数据库（保留原有功能）"""
    print("进入 save_memory_node 节点，开始处理...")
    
    # 兼容新旧状态格式
    maternal_id = state.get("maternal_id")
    if isinstance(maternal_id, str):
        maternal_id = maternal_id
    else:
        maternal_id = str(maternal_id)
    
    persist_directory = state.get("persist_directory") or f"/root/project2/data/vector_store/maternal_{maternal_id}"  # 修复：处理None值
    user_vector_dir = Path(persist_directory) / f"maternal_{maternal_id}"
    user_vector_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # 兼容处理chat_history字段
        chat_history_path = state.get("chat_history")
        if isinstance(chat_history_path, list):
            # 如果是列表格式，创建临时文件
            temp_file = Path(f"/tmp/temp_chat_{maternal_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(chat_history_path, f, ensure_ascii=False, indent=2)
            chat_history_path = str(temp_file)
        elif not chat_history_path:
            chat_history_path = "test/chat.json"  # 默认路径
        
        # 调用工具保存记忆
        save_memory.invoke({
            "chat_history": chat_history_path, 
            "persist_directory": str(user_vector_dir)
        })
        
        # 更新数据库记录
        try:
            db = get_session(get_db_engine())
            new_dialogue = MaternalDialogue(
                maternal_id=maternal_id,
                dialogue_content=chat_history_path,
                vector_store_path=str(user_vector_dir)
            )
            db.add(new_dialogue)
            db.commit()
            db.close()
        except Exception as db_error:
            logger.warning(f"数据库更新失败，但向量存储成功: {db_error}")
        
        # 完善状态信息
        state['content'] = f"成功存储对话记录到 {persist_directory}"
        state['metadata'] = {
            "chat_history_path": chat_history_path,
            "persist_directory": str(user_vector_dir),
            "timestamp": datetime.now().isoformat()
        }
        state['error'] = None
        print("记忆存储成功")
        return state
        
    except Exception as e:
        state['error'] = f"存储失败：{str(e)}"
        state['content'] = None
        state['metadata'] = None
        print(f"记忆存储失败：{str(e)}")
        return state

# 兼容性：保留原有的create_mem_agent函数
def create_mem_agent():
    """创建长期记忆智能体（兼容性函数）"""
    return create_enhanced_mem_agent()


if __name__ == '__main__':
    # 测试增强版记忆智能体
    enhanced_mem_agent = create_enhanced_mem_agent()
    
    # 测试状态
    test_state: MeMState = {
        "maternal_id": 1,
        "chat_id": "chat_1_pregnant_mother_test",
        "max_turns_in_memory": 3,  # 设置较小的值用于测试
    }
    
    # 执行智能体
    result_state = enhanced_mem_agent.invoke(test_state)
    
    # 打印处理结果
    print("\n增强版记忆智能体处理结果：")
    for key, value in result_state.items():
        if key in ["compressed_memory", "chat_history_text"] and value and len(str(value)) > 100:
            print(f"{key}: {str(value)[:100]}...")
        else:
            print(f"{key}: {value}")