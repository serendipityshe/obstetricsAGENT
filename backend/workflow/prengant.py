from typing import Annotated, TypedDict, List, Optional
from langgraph.graph import StateGraph, END, START
from langgraph.store.base import Op
from backend.agents import gen_synth_agent, mix_agent, create_retr_agent
from backend.api.v1.services.maternal_service import MaternalService
import logging

from test2 import maternal_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class PrengantState(TypedDict):
    """
    孕妇状态
    """
    input: Annotated[str, '用户输入']
    maternal_id: Annotated[int, '孕妇id(必填)']
    chat_id: Annotated[Optional[str], '聊天id(必填)']
    user_type: Annotated[str, '用户类型(必填)']
    timestamp: Annotated[Optional[str], '时间戳（格式：YYYY-MM-DD HH:MM:SS UTC，必填）']

    output: Annotated[str, '模型输出']
    context: Annotated[Optional[List[dict]], '上下文']
    retrieval_professor: Annotated[Optional[List[dict]], '专家知识库检索结果']
    retrieval_pregnant: Annotated[Optional[List[dict]], '孕妇知识库检索结果']

    file_id: Annotated[Optional[List[int]], "关联的文件ID列表"]
    image_path: Annotated[Optional[str], '图片路径']
    doc_path: Annotated[Optional[str], '文档路径']
    file_content: Annotated[Optional[str], '文件内容']

    error: Annotated[Optional[str], '错误信息']
    memory: Annotated[Optional[List[dict]], '记忆']
    
def _get_file_path(file_ids: Optional[List[int]], maternal_service: MaternalService) -> str:
    """
    获取文件路径
    """
    image_path = None
    doc_path = None
    try:
        for file_id in file_ids:
            logger.info(f"开始解析filed_id={file_id}的文件路径")
            file_info = maternal_service.get_medical_file_by_id(file_id)

            if not file_info:
                error_msg = f"file_id={file_id}未查询到对应文件信息"
                logger.error(error_msg)
                return None, None, error_msg
            
            file_type = file_info.get("file_type")
            file_path = file_info.get("file_path")
            if not file_type or not file_path:
                error_msg = f"file_id={file_id}文件类型或文件路径为空"
                logger.error(error_msg)
                return None, None, error_msg
            
            if file_type in ["png"]:
                image_path = file_path
                logger.info(f"图片路径={image_path}")
            elif file_type in ["pdf"]:
                doc_path = file_path
                logger.info(f"文档路径={doc_path}")
        return image_path, doc_path, None
    except Exception as e:
        error_msg = f"获取文件路径失败： {e}"
        logger.error(error_msg)
        return None, None, error_msg


def mix_node(state: PrengantState) -> PrengantState:
    """
    混合智能体节点
    """
    maternal_service = MaternalService()
    try:

        file_ids = state.get("file_id")
        image_path, doc_path, error_msg = _get_file_path(file_ids, maternal_service)
        if error_msg:
            state["error"] = error_msg
            state["image_path"] = None
            state["doc_path"] = None
            return state
        
        state["image_path"] = image_path
        state["doc_path"] = doc_path
        logger.info(f"路径解析完成， 图片路径={image_path}，文档路径={doc_path}")

        user_input = state.get("input")
        if not user_input:
            raise ValueError("混合处理节点失败： 用户输入(input)不能为空")

        mix_agent_instance = mix_agent()
        mix_input = {
            "input": user_input,
            "image_path": image_path,
            "doc_path": doc_path,
        }
        logger.info("启动混合智能体，开始融合用户输入与文件内容")
        mix_result = mix_agent_instance.invoke(mix_input)
        combined_result = mix_result.get("combined_results")
        if not combined_result:
            logger.warning("混合智能体未返回有效融合内容（无文件或内容为空）")
            state["file_content"] = None
            return state
        
        if not combined_result:
            raise ValueError("混合处理节点失败： 融合结果为空")
        state["file_content"] = "\n\n".join([
            f"文件内容： {str(item['content']).strip()}\n元数据： {item['metadata']}"
            for item in combined_result
        ])
        logger.info(f"混合智能体处理成功：融合{len(combined_result)}个来源的内容")
    except Exception as e:
        # 捕获全流程异常，存入state供前端展示
        error_msg = f"混合节点执行失败：{str(e)}"
        logger.error(f"{error_msg}")
        state["error"] = error_msg
        state["context"] = None
        state["file_content"] = None
    return state

def _get_vector_path(
    maternal_id: int,
    maternal_service: MaternalService
) -> str:
    """
    获取个人向量数据库路径
    """
    try:
        vector_db_path = maternal_service.get_dialogues(maternal_id)
        if not vector_db_path:
            raise ValueError(f"未查询到孕妇{maternal_id}的向量数据库路径")
        return vector_db_path
    except Exception as e:
        error_msg = f"获取向量数据库路径失败：{str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

def retr_node(state: PrengantState) -> PrengantState:
    """
    检索节点
    """
    try:
        maternal_id = state.get("maternal_id")
        vector_db_path_pregnant = _get_vector_path(maternal_id, maternal_service)
        vector_db_professor = "./data/vector_store_json"
        retr_agent_instance = create_retr_agent()
        retr_input = {
            "input": state.get("input"),
            "vector_db_professor": vector_db_professor,
            "vector_db_pregnant": vector_db_path_pregnant,
        }
        retr_result = retr_agent_instance.invoke(retr_input)
        state["retrieval_professor"] = retr_result.get("output")['专家知识库']
        state["retrieval_pregnant"] = retr_result.get("output")['孕妇知识库']
        logger.info(f"检索智能体处理成功：检索到{len(state['retrieval_professor'])}条专家知识库结果，{len(state['retrieval_pregnant'])}条孕妇知识库结果")
    except Exception as e:
        error_msg = f"检索节点执行失败：{str(e)}"
        logger.error(f"{error_msg}")
        state["error"] = error_msg
        state["retrieval"] = None
    return state

def proc_context(state: PrengantState) -> PrengantState:
    """
    处理上下文
    """
    try:
        context = ""
        file_content = state.get("file_content")
        if not file_content:
            raise ValueError("处理上下文节点失败： 文件内容(file_content)不能为空")
        retrieval_professor = state.get("retrieval_professor")
        retrieval_pregnant = state.get("retrieval_pregnant")
        context.join([file_content, retrieval_professor, retrieval_pregnant])
        context = context.replace("\n", "")
        state["context"] = context
    except Exception as e:
        error_msg = f"处理上下文节点执行失败：{str(e)}"
        logger.error(f"{error_msg}")
        state["error"] = error_msg
        state["context"] = None
    return state

def gen_synth_node(state: PrengantState) -> PrengantState:
    """
    生成合成智能体节点
    """
    try:
        gen_synth_agent_instance = gen_synth_agent()
        gen_synth_input = {
            "input": state.get("input"),
            "user_type": state.get("user_type"),
            "context": state.get("context"),
        }
        logger.info("启动合成智能体，开始生成合成输出")
        gen_synth_result = gen_synth_agent_instance.invoke(gen_synth_input)
        state["output"] = gen_synth_result.get("output")
        logger.info(f"合成智能体处理成功：生成输出={state['output']}")
    except Exception as e:
        # 捕获全流程异常，存入state供前端展示
        error_msg = f"合成节点执行失败：{str(e)}"
        logger.error(f"{error_msg}")
        state["error"] = error_msg
        state["output"] = None
    return state

def prengant_workflow():
    """
    孕妇工作流
    """
    builder = StateGraph(PrengantState)
    builder.add_node("gen_synth", gen_synth_node)
    builder.add_node("retr", retr_node)
    builder.add_node("proc_context", proc_context)
    builder.add_node("mix", mix_node)
    builder.add_edge(START, "mix")
    builder.add_edge(START, "retr")
    builder.add_edge("mix", "gen_synth")
    builder.add_edge("retr", "gen_synth")
    builder.add_edge("mix", "proc_context")
    builder.add_edge("retr", "proc_context")
    builder.add_edge("proc_context", "gen_synth")
    builder.add_edge("gen_synth", END)

    graph = builder.compile()
    return graph

if __name__ == "__main__":
    graph = prengant_workflow()
    graph.invoke({
        "input": "孕妇的症状",
        "user_type": "孕妇",
        "maternal_id": 1,
    })

    