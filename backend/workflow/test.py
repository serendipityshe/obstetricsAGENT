import sys
from pathlib import Path
from typing import Annotated, TypedDict, List, Optional, Tuple
import datetime

root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

from langgraph.graph import StateGraph, END, START
from backend.agents import gen_synth_agent, mix_agent, create_retr_agent
from backend.api.v1.services.maternal_service import MaternalService
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class PrengantState(TypedDict):
    """孕妇状态（修正：context改为字符串类型，匹配实际拼接结果）"""
    input: Annotated[str, '用户输入']
    maternal_id: Annotated[int, '孕妇id(必填)']
    chat_id: Annotated[str, '聊天id(必填)']
    user_type: Annotated[str, '用户类型(必填)']
    timestamp: Annotated[str, '时间戳（格式：YYYY-MM-DD HH:MM:SS UTC，必填）']

    output: Annotated[str, '模型输出']
    context: Annotated[Optional[str], '上下文（拼接后的字符串）']  # 修正：List[dict]→str
    retrieval_professor: Annotated[Optional[List[dict]], '专家知识库检索结果']
    retrieval_pregnant: Annotated[Optional[List[dict]], '孕妇知识库检索结果']

    file_id: Annotated[Optional[List[str]], "文件路径"]
    image_path: Annotated[Optional[str], '图片路径']
    doc_path: Annotated[Optional[str], '文档路径']
    file_content: Annotated[Optional[str], '文件内容']

    error: Annotated[Optional[str], '错误信息']
    memory: Annotated[Optional[List[dict]], '记忆']
    
def _get_file_path(file_ids: List[int]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """获取文件路径（补充maternal_id参数，适配服务层调用）"""
    image_path = None
    doc_path = None
    try:    
        for file_path in file_ids:
            file_type = file_path.split(".")[-1]
            if file_type in ["png", "jpg", "jpeg"]:  # 扩展图片类型覆盖更多场景
                image_path = file_path
                logger.info(f"图片路径={image_path}")
            elif file_type in ["pdf", "docx", "txt", "json", "doc", "csv"]:  # 扩展文档类型
                doc_path = file_path
                logger.info(f"文档路径={doc_path}")
        return image_path, doc_path, None
    except Exception as e:
        error_msg = f"获取文件路径失败： {e}"
        logger.error(error_msg)
        return None, None, error_msg


def mix_node(state: PrengantState) -> dict:
    """混合智能体节点（补充maternal_id参数传递）"""
    updates = {}
    try:
        file_ids = state.get("file_id")
        # 修正：传递maternal_id给_get_file_path，适配服务层查询
        image_path, doc_path, error_msg = _get_file_path(file_ids)
        if error_msg:
            updates["error"] = error_msg
            updates["image_path"] = None
            updates["doc_path"] = None
            return updates
        
        updates["image_path"] = image_path
        updates["doc_path"] = doc_path
        logger.info(f"路径解析完成， 图片路径={image_path}，文档路径={doc_path}")

        user_input = state.get("input")
        if not user_input:
            raise ValueError("混合处理节点失败： 用户输入(input)不能为空")

        mix_agent_instance = mix_agent()
        mix_input = {
            "input": user_input,
            "img_file_path": image_path or "",
            "doc_file_path": doc_path or "",
        }
        logger.info("启动混合智能体，开始融合用户输入与文件内容")
        mix_result = mix_agent_instance.invoke(mix_input)
        print("mix_result", mix_result)
        combined_result = mix_result.get("combined_results")
        print("combined_result", combined_result)
        if not combined_result:
            logger.warning("混合智能体未返回有效融合内容（无文件或内容为空）")
            updates["file_content"] = None
            return updates
        
        updates["file_content"] = "\n\n".join([
            f"文件内容： {str(item['content']).strip()}\n元数据： {item['metadata']}"
            for item in combined_result
        ])
        logger.info(f"混合智能体处理成功：融合{len(combined_result)}个来源的内容")
    except Exception as e:
        error_msg = f"混合节点执行失败：{str(e)}"
        logger.error(f"{error_msg}")
        updates["error"] = error_msg
        updates["file_content"] = None
    return updates

def _get_vector_path(maternal_id: int, chat_id: str, maternal_service: MaternalService) -> str:
    """获取个人向量数据库路径（修复：处理单个MaternalDialogue对象）"""
    try:
        # 修正：get_dialogues返回单个ORM对象（非列表），需判断类型
        dialogues = maternal_service.get_dialogues(maternal_id, chat_id)
        if not isinstance(dialogues, list):
            dialogues = [dialogues]

        if not dialogues:
            logger.warning(f"未查询到孕妇{maternal_id}的对话记录。默认使用空字符串")
            return ""
        
        # 修正：ORM对象用属性访问（非字典get），适配服务层返回格式
        first_dialogue = dialogues[0]
        vector_db_path = first_dialogue['vector_store_path']
        if not vector_db_path:
            logger.warning(f"孕妇{maternal_id}的对话记录中无向量数据库路径，默认使用空字符串")
            return ""
        return vector_db_path
    except Exception as e:
        error_msg = f"获取向量数据库路径失败：{str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

def retr_node(state: PrengantState) -> dict:
    """检索节点（无新增修改，依赖_get_vector_path修复）"""
    updates = {}
    try:
        maternal_service = MaternalService()
        maternal_id = state.get("maternal_id")
        chat_id = state.get("chat_id")
        if not maternal_id or not chat_id:
            raise ValueError("maternal_id和chat_id不能为空")
        vector_db_path_pregnant = _get_vector_path(maternal_id, chat_id, maternal_service)
        vector_db_professor = "/root/project2/data/vector_store_json"
        retr_agent_instance = create_retr_agent()
        retr_input = {
            "input": state.get("input"),
            "vector_db_professor": vector_db_professor,
            "vector_db_pregnant": vector_db_path_pregnant,
        }
        retr_result = retr_agent_instance.invoke(retr_input)
        logger.info("检索智能体调用完成，开始校验结果")
        output_data = retr_result.get("output", {})
        print(type(output_data))
        print("output: ", output_data)
        retrieval_professor = output_data["专家知识库"]
        retrieval_pregnant = output_data["孕妇知识库"]

        if not retrieval_professor:
            raise ValueError(f"专家知识库检索结果为空，无法提供专业建议（maternal_id: {maternal_id}）")
        if not retrieval_pregnant:
            logger.warning(
                f"孕妇{maternal_id}的个人知识库检索结果为空，无法提供个性化建议"
            )
        updates["retrieval_professor"] = retrieval_professor
        updates["retrieval_pregnant"] = retrieval_pregnant
        logger.info(f"检索智能体处理成功：检索到{len(retrieval_professor)}条专家知识库结果，{len(retrieval_pregnant)}条孕妇知识库结果")
    except Exception as e:
        error_msg = f"检索节点执行失败：{str(e)}"
        logger.error(error_msg)
        updates["error"] = error_msg
        updates["retrieval_professor"] = None
        updates["retrieval_pregnant"] = None
    return updates

def proc_context(state: PrengantState) -> PrengantState:
    """处理上下文（适配context字符串类型）"""
    try:
        file_content = state.get("file_content") or ""  # 空值默认空字符串
        # 检索结果转为字符串（避免None导致拼接报错）
        retrieval_professor_str = str(state.get("retrieval_professor", []))
        retrieval_pregnant_str = str(state.get("retrieval_pregnant", []))
        
        # 拼接上下文（按优先级排序：文件内容→孕妇知识库→专家知识库）
        context_parts = [
            f"【文件内容】\n{file_content}",
            f"【孕妇个人知识库】\n{retrieval_pregnant_str}",
            f"【专家通用知识库】\n{retrieval_professor_str}"
        ]
        context = "\n\n".join(part for part in context_parts if part.strip())
        state["context"] = context
        logger.info(f"上下文处理完成，总长度：{len(context)}字符")
    except Exception as e:
        error_msg = f"处理上下文节点执行失败：{str(e)}"
        logger.error(f"{error_msg}")
        state["error"] = error_msg
        state["context"] = None
    return state

def gen_synth_node(state: PrengantState) -> PrengantState:
    """生成合成智能体节点（无修改）"""
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
        logger.info(f"合成智能体处理成功：生成输出={state['output'][:50]}...")  # 截断长输出避免日志冗余
    except Exception as e:
        error_msg = f"合成节点执行失败：{str(e)}"
        logger.error(f"{error_msg}")
        state["error"] = error_msg
        state["output"] = None
    return state

def prengant_workflow():
    """孕妇工作流（修复：并行节点改为串行，避免更新冲突）"""
    builder = StateGraph(PrengantState)
    builder.add_node("gen_synth", gen_synth_node)
    builder.add_node("retr", retr_node)
    builder.add_node("proc_context", proc_context)
    builder.add_node("mix", mix_node)

    # 修正：将并行（START→mix + START→retr）改为串行（START→mix→retr→proc_context）
    # 避免两个节点同时操作state导致更新冲突
    builder.add_edge(START, "mix")
    builder.add_edge(START, 'retr')
    builder.add_edge("mix", "proc_context")
    builder.add_edge("retr", "proc_context")
    builder.add_edge("proc_context", "gen_synth")
    builder.add_edge("gen_synth", END)

    graph = builder.compile()
    return graph

if __name__ == "__main__":
    graph = prengant_workflow()
    # 构造完整的输入参数（含必填字段）
    input_data = {
        "input": "孕妇最近出现头晕症状，需要什么建议？",
        "user_type": "孕妇",
        "maternal_id": 1,
        "chat_id": f"chat_{int(datetime.datetime.now().timestamp())}",  # 生成唯一整数chat_id
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file_id": ["/root/project2/test/孕前和孕期保健指南.doc"] # 无文件时显式传None，避免state字段缺失
    }
    # 执行工作流并打印结果
    result = graph.invoke(input_data)
    logger.info("="*50)
    logger.info("工作流执行结果：")
    logger.info(f"错误信息：{result.get('error') or '无'}")
    logger.info(f"生成输出：{result.get('output') or '无'}")
    logger.info(f"上下文：{result.get('context')[:100]}" if result.get('context') else "上下文：无")
    