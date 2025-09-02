import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from typing import TypedDict, Optional, Dict, Annotated
from langgraph.graph import StateGraph, END, START
from backend.agents.tools.tools import save_memory  # 确保该工具正确实现
from datetime import datetime


class MeMState(TypedDict):
    """完善长期记忆智能体状态定义"""
    chat_history: Annotated[str, "对话记录路径"]
    persist_directory: Annotated[str, "向量数据库路径"]
    error: Optional[Annotated[str, '错误信息']]
    content: Optional[Annotated[str, '处理结果信息']]  # 新增：存储处理结果
    metadata: Optional[Annotated[Dict, '附加元数据']]  # 新增：存储元数据


def save_memory_node(state: MeMState) -> MeMState:
    """长期记忆智能体节点：保存对话记录到向量数据库"""
    print("进入 save_memory_node 节点，开始处理...")  # 验证节点是否执行
    try:
        # 调用工具保存记忆（确保 save_memory.invoke 正确实现）
        save_memory.invoke({
            "chat_history": state['chat_history'], 
            "persist_directory": state['persist_directory']
        })
        
        # 完善状态信息（此时字段已在 MeMState 中定义，会被保留）
        state['content'] = f"成功存储对话记录到 {state['persist_directory']}"
        state['metadata'] = {
            "chat_history_path": state['chat_history'],
            "persist_directory": state['persist_directory'],
            "timestamp": datetime.now().isoformat()  # 可添加时间戳等信息
        }
        state['error'] = None  # 清除错误信息
        print("记忆存储成功")
        return state
    except Exception as e:
        state['error'] = f"存储失败：{str(e)}"
        state['content'] = None
        state['metadata'] = None
        print(f"记忆存储失败：{str(e)}")
        return state


def create_mem_agent():
    """创建长期记忆智能体"""
    builder = StateGraph(MeMState)
    builder.add_node("save_memory", save_memory_node)  # 添加节点
    builder.add_edge(START, "save_memory")  # 起始节点 -> 存储节点
    builder.add_edge("save_memory", END)    # 存储节点 -> 结束
    return builder.compile()


if __name__ == '__main__':
    mem_agent = create_mem_agent()
    # 初始状态
    initial_state = {
        "chat_history": "test/chat.json",  # 确保该路径存在实际文件
        "persist_directory": "test/vector_db",  # 确保该目录可写
        "error": None,
        "content": None,
        "metadata": None
    }
    
    # 执行智能体并捕获处理后的状态（关键：接收返回的新状态）
    result_state = mem_agent.invoke(initial_state)
    
    # 打印处理结果（此时能看到节点处理后的状态）
    print("\n处理后的状态：")
    for key, value in result_state.items():
        print(f"{key}: {value}")