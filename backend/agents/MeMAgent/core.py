"""
长期记忆存储智能体
负责存储和管理长期记忆，确保信息的持久化和检索。
"""

from typing import TypedDict, Optional, Dict, Annotated
from langgraph.graph import StateGraph, END, START
from backend.agents.tools.tools import save_memory


class MeMState(TypedDict):
    """
    长期记忆智能体状态定义
    """
    chat_history: Annotated[list, "对话记录"]
    persist_directory: Annotated[str, "向量数据库路径"]
    error: Optional[Annotated[str, '错误信息']] 


#--------------------------定义节点------------------------------------
def save_memory_node(state: MeMState) -> MeMState:
    """
    长期记忆智能体节点
    负责将对话记录保存到向量数据库中用于后续的语义检索
    """
    try:
        save_memory(state['chat_history'], state['persist_directory'])
        state['content'] = f"成功存储{len(state['chat_history'])}条记忆"
        state['metadata'] = {"persist_directory": state['persist_directory']}
        return state
    except Exception as e:
        state['error'] = str(e)
        return state

#------------------------------定义流程------------------------------------
def create_mem_agent():
    """
    创建长期记忆智能体
    """
    builder = StateGraph(MeMState)

    #添加节点
    builder.add_node("save_memory", save_memory_node)

    #添加边
    builder.add_edge(START, "save_memory")
    builder.add_edge("save_memory", END)

    #编译图
    graph = builder.compile()
    return graph

if __name__ == '__main__':
    mem_agent = create_mem_agent()
    state = {
        "chat_history": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么我可以帮助你的吗？"},
        ],
        "persist_directory": "./vector_db",
    }
    mem_agent.invoke(state)
    print(state)
