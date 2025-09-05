from typing import Annotated, TypedDict, List, Optional
from langgraph.graph import StateGraph, END, START
from backend.agents import gen_synth_agent, mix_agent, create_retr_agent

class PrengantState(TypedDict):
    """
    孕妇状态
    """
    input: Annotated[str, '用户输入']
    output: Annotated[str, '模型输出']
    maternal_id: Annotated[str, '孕妇id']
    error: Annotated[Optional[str], '错误信息']
    context: Annotated[Optional[List[dict]], '上下文']
    memory: Annotated[Optional[List[dict]], '记忆']
    retrieval: Annotated[Optional[List[dict]], '检索']

def mix_node(state: PrengantState) -> PrengantState:
    """
    混合智能体节点
    """
    pass 

def gen_synth_node(state: PrengantState) -> PrengantState:
    """
    生成合成智能体节点
    """
    pass

def retr_node(state: PrengantState) -> PrengantState:
    """
    检索节点
    """
    pass

def prengant_workflow():
    """
    孕妇工作流
    """
    builder = StateGraph(PrengantState)
    builder.add_node("gen_synth", gen_synth_node)
    builder.add_node("retr", retr_node)
    builder.add_node("mix", mix_node)
    builder.add_edge(START, "mix")
    builder.add_edge(START, "retr")
    builder.add_edge("mix", "gen_synth")
    builder.add_edge("retr", "gen_synth")
    builder.add_edge("gen_synth", END)

    graph = builder.compile()
    return graph

    