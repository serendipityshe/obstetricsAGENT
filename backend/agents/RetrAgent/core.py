"""
检索智能体
负责从专家知识库和个人知识库中进行检索
"""
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from typing import TypedDict, Optional, List, Annotated, Dict, Any
from langgraph.graph import StateGraph, END, START

from backend.agents.tools.tools import rag_tool

class RetrAgentStateRequired(TypedDict):
    """
    检索智能体状态 - 必需字段
    """
    input: Annotated[str, '用户输入']
    vector_db_professor: Annotated[str, '向量数据库（专家知识库）']
    vector_db_pregnant: Annotated[str, '向量数据库（孕妇知识库）']

class RetrAgentState(RetrAgentStateRequired, total=False):
    """
    检索智能体状态 - 包含可选字段
    """
    output: Annotated[Optional[Dict[str, Any]], '检索结果']
    error: Annotated[Optional[str], '错误信息']

def retreive_node(state: RetrAgentState) -> RetrAgentState:
    """
    检索智能体节点
    """
    try:
        # 修复：使用正确的rag_tool调用方式
        retr_medical_data = rag_tool.invoke({
            "user_query": state['input'],
            "vector_store_path": state['vector_db_professor'],
            "top_k": 3
        })
        retr_pregnant_data = rag_tool.invoke({
            "user_query": state['input'],
            "vector_store_path": state['vector_db_pregnant'], 
            "top_k": 3
        })
        
        # 确保返回结果的结构正确
        professor_fragments = retr_medical_data.get("knowledge_fragments", []) if retr_medical_data else []
        pregnant_fragments = retr_pregnant_data.get("knowledge_fragments", []) if retr_pregnant_data else []
        
        state['output'] = {
            "专家知识库": professor_fragments,
            "孕妇知识库": pregnant_fragments,
        }
        state['error'] = None
    except Exception as e:
        state['output'] = {
            "专家知识库": [],
            "孕妇知识库": [],
        }
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
    state: RetrAgentState = {
        "input": "孕妇如何预防感冒",
        "vector_db_professor": "./data/vector_store_json",
        "vector_db_pregnant": "vector_db_pregnant",
    }
    result = agent.invoke(state)
    print(result)