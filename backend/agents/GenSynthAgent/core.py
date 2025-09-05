from nt import error
from typing import Annotated, Optional, List, TypedDict
from langgraph.graph import StateGraph, END, START
from backend.agents.tools.tools import qwen_tool
from backend.prompt_engineering.strategies.template_selector import TemplateSelector

class GenSynthAgentState(TypedDict):
    """
    生成合成智能体
    """
    input: Annotated[str, "用户输入"]
    output: Annotated[str, "生成结果"]
    context: Annotated[str, "上下文"]
    error: Annotated[Optional[str], "错误信息"]

def gen_synth_node(state: GenSynthAgentState) -> GenSynthAgentState:
    """
    生成合成智能体节点
    """
    try:
        template_selector = TemplateSelector()
        template = template_selector.select_template(state['input'])
        template = template.format(input=state['input'], context=state['context'])
        state['output'] = qwen_tool.invoke({
            "prompt": template,
        })
        state['error'] = None
    except Exception as e:
        state['output'] = None
        state['error'] = f"生成失败：{str(e)}"
    return state

def gen_synth_agent():
    """
    生成合成智能体
    """
    builder = StateGraph(GenSynthAgentState)
    builder.add_node("gen_synth_node", gen_synth_node)
    builder.add_edge(START, "gen_synth_node")
    builder.add_edge("gen_synth_node", END)
    return builder.compile()


