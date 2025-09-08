"""
检索智能体
负责从专家知识库和个人知识库中进行检索
"""
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from typing import TypedDict, Optional, List, Annotated
from langgraph.graph import StateGraph, END, START

from backend.agents.tools.tools import rag_tool

class RetrAgentState(TypedDict):
    """
    检索智能体状态
    """
    input: Annotated[str, '用户输入']
    vector_db_professor: Annotated[str, '向量数据库（专家知识库）']
    vector_db_pregnant: Annotated[str, '向量数据库（孕妇知识库）']
    output: Annotated[str, '检索结果']
    error: Annotated[Optional[str], '错误信息']

def retreive_node(state: RetrAgentState) -> RetrAgentState:
    """
    检索智能体节点
    """
    try:
        retr_medical_data = rag_tool.invoke({
            "user_query": state['input'],
            "vector_store_path": state['vector_db_professor'],
        })
        retr_pregnant_data = rag_tool.invoke({
            "user_query": state['input'],
            "vector_store_path": state['vector_db_pregnant'],
        })
        state['output'] = {
            "专家知识库": retr_medical_data,
            "孕妇知识库": retr_pregnant_data,
        }
        state['error'] = None
    except Exception as e:
        state['output'] = None
        state['error'] = f"检索失败：{str(e)}"
    return state


def create_retr_agent():
    """
    创建检索智能体
    """
    builder = StateGraph(RetrAgentState)
    builder.add_node("retrieve_node", retreive_node)
    builder.add_edge(START, "retrieve_node")
    builder.add_edge("retrieve_node", END)
    return builder.compile()

if __name__ == '__main__':
    agent = create_retr_agent()
    state = {
        "input": "孕妇如何预防感冒",
        "vector_db_professor": "./data/vector_store_json",
        "vector_db_pregnant": "vector_db_pregnant",
    }
    result = agent.invoke(state)
    print(result)