import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))



from typing import Annotated, TypedDict, List, Optional, Union
from langgraph.graph import StateGraph, END, START
from backend.agents import gen_synth_agent, mix_agent, create_retr_agent
from backend.api.v1.services.maternal_service import MaternalService
import logging
import datetime 


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class PrengantState(TypedDict):
    """
    孕妇状态（调整file相关字段为列表以支持多文件，兼容空值）
    """
    input: Annotated[str, '用户输入(必填)']
    maternal_id: Annotated[int, '孕妇id(必填)']
    chat_id: Annotated[Optional[str], '聊天id(必填)']
    user_type: Annotated[str, '用户类型(必填)']
    timestamp: Annotated[Optional[str], '时间戳（格式：YYYY-MM-DD HH:MM:SS UTC，必填）']

    output: Annotated[Optional[str], '模型输出']
    context: Annotated[Optional[str], '上下文（修改为字符串，适配后续拼接逻辑）']
    retrieval_professor: Annotated[Optional[List[dict]], '专家知识库检索结果']
    retrieval_pregnant: Annotated[Optional[List[dict]], '孕妇知识库检索结果']

    file_id: Annotated[Optional[List[int]], "关联的文件ID列表（可为空）"]
    image_path: Annotated[Optional[List[str]], '图片路径列表（支持多文件）']
    doc_path: Annotated[Optional[List[str]], '文档路径列表（支持多文件）']
    file_content: Annotated[Optional[str], '文件内容拼接结果（可为空）']

    error: Annotated[Optional[str], '错误信息']
    memory: Annotated[Optional[List[dict]], '记忆']


def _get_file_path(file_ids: Optional[List[int]], maternal_service: MaternalService) -> tuple[Optional[List[str]], Optional[List[str]], Optional[str]]:
    """
    修复：支持多文件路径存储（不再覆盖），兼容file_ids为空
    返回：图片路径列表、文档路径列表、错误信息
    """
    image_paths = []  # 改为列表存储多图片
    doc_paths = []    # 改为列表存储多文档
    if not file_ids or len(file_ids) == 0:
        logger.info("file_ids为空，无需解析文件路径")
        return None, None, None  # 空时返回None，不抛错
    
    try:
        for file_id in file_ids:
            logger.info(f"开始解析file_id={file_id}的文件路径")
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
            
            if file_type.lower() in ["png", "jpg", "jpeg"]:  # 扩展图片格式支持
                image_paths.append(file_path)
                logger.info(f"新增图片路径：{file_path}")
            elif file_type.lower() in ["pdf", "docx"]:  # 扩展文档格式支持
                doc_paths.append(file_path)
                logger.info(f"新增文档路径：{file_path}")
        
        # 无匹配文件类型时返回空列表
        return image_paths if image_paths else None, doc_paths if doc_paths else None, None
    except Exception as e:
        error_msg = f"获取文件路径失败： {str(e)}"
        logger.error(error_msg)
        return None, None, error_msg


def mix_node(state: PrengantState) -> PrengantState:
    """
    混合智能体节点（仅当file_ids非空时执行）
    """
    # 统一创建MaternalService实例（避免导入冲突）
    maternal_service = MaternalService()
    try:
        file_ids = state.get("file_id")
        # 调用修复后的文件路径解析函数
        image_paths, doc_paths, error_msg = _get_file_path(file_ids, maternal_service)
        
        if error_msg:
            state["error"] = error_msg
            state["image_path"] = None
            state["doc_path"] = None
            return state
        
        state["image_path"] = image_paths
        state["doc_path"] = doc_paths
        logger.info(f"路径解析完成：图片路径={image_paths}，文档路径={doc_paths}")

        user_input = state.get("input")
        if not user_input:
            raise ValueError("用户输入(input)不能为空")

        # 调用混合智能体
        mix_agent_instance = mix_agent()
        mix_input = {
            "input": user_input,
            "image_path": image_paths,  # 传列表（适配多文件）
            "doc_path": doc_paths,      # 传列表（适配多文件）
        }
        logger.info("启动混合智能体，融合用户输入与文件内容")
        mix_result = mix_agent_instance.invoke(mix_input)
        combined_result = mix_result.get("combined_results")

        if not combined_result or len(combined_result) == 0:
            logger.warning("混合智能体未返回有效融合内容，设为None")
            state["file_content"] = None
            return state
        
        # 拼接多文件内容（保留元数据）
        state["file_content"] = "\n\n".join([
            f"【文件类型：{item.get('metadata', {}).get('file_type', '未知')}】\n"
            f"文件路径：{item.get('metadata', {}).get('file_path', '未知')}\n"
            f"内容：{str(item.get('content', '')).strip()}"
            for item in combined_result
        ])
        logger.info(f"混合智能体处理成功：融合{len(combined_result)}个文件内容")
    except Exception as e:
        error_msg = f"混合节点执行失败：{str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["file_content"] = None
        state["image_path"] = None
        state["doc_path"] = None
    return state


def _get_vector_path(maternal_id: int, maternal_service: MaternalService) -> str:
    """获取个人向量数据库路径（无修改，保持原逻辑）"""
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
    """检索节点（无论file_ids是否为空，都必须执行）"""
    maternal_service = MaternalService()
    try:
        maternal_id = state.get("maternal_id")
        if not maternal_id:
            raise ValueError("孕妇id(maternal_id)不能为空")
        
        # 获取向量库路径
        vector_db_path_pregnant = _get_vector_path(maternal_id, maternal_service)
        vector_db_professor = "./data/vector_store_json"
        
        # 调用检索智能体
        retr_agent_instance = create_retr_agent()
        retr_input = {
            "input": state.get("input"),
            "vector_db_professor": vector_db_professor,
            "vector_db_pregnant": vector_db_path_pregnant,
        }
        retr_result = retr_agent_instance.invoke(retr_input)
        
        # 提取检索结果（兼容不同返回格式）
        retrieval_output = retr_result.get("output", {})
        state["retrieval_professor"] = retrieval_output.get("专家知识库", [])
        state["retrieval_pregnant"] = retrieval_output.get("孕妇知识库", [])
        
        logger.info(
            f"检索智能体处理成功：\n"
            f"- 专家知识库：{len(state['retrieval_professor'])}条结果\n"
            f"- 孕妇知识库：{len(state['retrieval_pregnant'])}条结果"
        )
    except Exception as e:
        error_msg = f"检索节点执行失败：{str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["retrieval_professor"] = None
        state["retrieval_pregnant"] = None
    return state


def decide_mix_node(state: PrengantState) -> Union[str, PrengantState]:
    """
    新增：分支判断节点（核心逻辑）
    根据file_ids是否为空，决定是否执行mix_agent：
    - file_ids非空 → 执行mix节点
    - file_ids为空 → 跳过mix节点，直接进入proc_context
    """
    file_ids = state.get("file_id")
    # 判断file_ids是否为空（None或空列表）
    if file_ids and len(file_ids) > 0:
        logger.info(f"检测到file_ids={file_ids}，将执行mix_agent")
        return "mix"  # 下一个节点：mix
    else:
        logger.info("未检测到有效file_ids，跳过mix_agent")
        # 为空时主动设file_content为None（避免后续上下文处理异常）
        state["file_content"] = None
        return "proc_context"  # 下一个节点：直接处理上下文


def proc_context(state: PrengantState) -> PrengantState:
    """
    修复：兼容file_content为空（跳过mix时），正确拼接上下文
    """
    try:
        context_parts = []  # 用列表收集各部分上下文，最后拼接
        
        # 1. 添加文件内容（若有）
        file_content = state.get("file_content")
        if file_content:
            context_parts.append(f"【文件参考内容】\n{file_content}")
            logger.info("上下文已加入文件内容")
        
        # 2. 添加专家知识库检索结果（若有）
        retrieval_professor = state.get("retrieval_professor")
        if retrieval_professor and len(retrieval_professor) > 0:
            prof_str = "\n\n".join([
                f"专家观点{idx+1}：\n{item.get('content', '无内容')}\n"
                f"来源：{item.get('metadata', {}).get('source', '未知')}"
                for idx, item in enumerate(retrieval_professor)
            ])
            context_parts.append(f"【专家知识库参考】\n{prof_str}")
            logger.info(f"上下文已加入{len(retrieval_professor)}条专家结果")
        
        # 3. 添加孕妇知识库检索结果（若有）
        retrieval_pregnant = state.get("retrieval_pregnant")
        if retrieval_pregnant and len(retrieval_pregnant) > 0:
            preg_str = "\n\n".join([
                f"个人记录{idx+1}：\n{item.get('content', '无内容')}\n"
                f"时间：{item.get('metadata', {}).get('timestamp', '未知')}"
                for idx, item in enumerate(retrieval_pregnant)
            ])
            context_parts.append(f"【孕妇个人记录参考】\n{preg_str}")
            logger.info(f"上下文已加入{len(retrieval_pregnant)}条孕妇记录")
        
        # 4. 拼接所有上下文（无内容时设为空字符串，避免None）
        if len(context_parts) == 0:
            state["context"] = ""
            logger.warning("上下文无有效内容（无文件+无检索结果）")
        else:
            state["context"] = "\n\n" + "-"*50 + "\n\n".join(context_parts)
            logger.info(f"上下文处理完成，总长度：{len(state['context'])}字符")
    
    except Exception as e:
        error_msg = f"处理上下文节点执行失败：{str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["context"] = None
    return state


def gen_synth_node(state: PrengantState) -> PrengantState:
    """生成合成智能体节点（无修改，适配context字段）"""
    try:
        # 先检查前置条件（避免无效调用）
        if state.get("error"):
            raise ValueError(f"前置节点存在错误：{state['error']}")
        if not state.get("input"):
            raise ValueError("用户输入(input)不能为空")
        if not state.get("user_type"):
            raise ValueError("用户类型(user_type)不能为空")
        
        # 调用生成合成智能体
        gen_synth_agent_instance = gen_synth_agent()
        gen_synth_input = {
            "input": state["input"],
            "user_type": state["user_type"],
            "context": state.get("context", ""),  # 空上下文时传空字符串
            "error": state.get("error")
        }
        logger.info("启动合成智能体，生成最终输出")
        gen_synth_result = gen_synth_agent_instance.invoke(gen_synth_input)
        
        # 提取生成结果（兼容不同返回格式）
        state["output"] = gen_synth_result.get("output") or "未生成有效输出"
        logger.info(f"合成智能体处理成功：\n输出内容：{state['output'][:100]}...")  # 打印前100字符避免过长
    
    except Exception as e:
        error_msg = f"合成节点执行失败：{str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["output"] = None
    return state


def prengant_workflow():
    """
    修复：工作流逻辑（新增分支判断，调整节点顺序）
    核心流程：
    START → 并行执行【分支判断+检索】→ 统一处理上下文 → 生成输出 → END
    """
    builder = StateGraph(PrengantState)
    
    # 1. 添加所有节点（含新增的分支判断节点）
    builder.add_node("decide_mix", decide_mix_node)  # 分支判断节点
    builder.add_node("mix", mix_node)                # 混合智能体节点
    builder.add_node("retr", retr_node)              # 检索节点
    builder.add_node("proc_context", proc_context)    # 上下文处理节点
    builder.add_node("gen_synth", gen_synth_node)    # 生成合成节点
    
    # 2. 核心边配置（按分支逻辑连接）
    # 2.1 START → 并行触发：分支判断 + 检索（检索无论是否有文件都要执行）
    builder.add_edge(START, "decide_mix")
    builder.add_edge(START, "retr")
    
    # 2.2 分支判断结果 → 对应节点
    builder.add_edge("decide_mix", "mix")            # file_ids非空 → 执行mix
    builder.add_edge("decide_mix", "proc_context")   # file_ids为空 → 跳过mix
    
    # 2.3 mix节点执行完 → 必须处理上下文
    builder.add_edge("mix", "proc_context")
    
    # 2.4 检索节点执行完 → 必须处理上下文（与mix结果汇合）
    builder.add_edge("retr", "proc_context")
    
    # 2.5 上下文处理完 → 生成最终输出
    builder.add_edge("proc_context", "gen_synth")
    
    # 2.6 生成输出 → 结束
    builder.add_edge("gen_synth", END)
    
    # 编译工作流（启用并行执行，确保retr和decide_mix同时跑）
    graph = builder.compile(interrupt_before=[], interrupt_after=[])
    return graph


if __name__ == "__main__":
    # 初始化工作流
    graph = prengant_workflow()
    
    # 测试两种场景：
    # 场景1：file_ids为空（跳过mix_agent）
    test_state_empty_file = {
        "input": "孕妇如何缓解孕期便秘？",
        "user_type": "孕妇",
        "maternal_id": 1,
        "chat_id": "chat_20250906_001",  # 补充必填的chat_id
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 补充必填时间戳
        "file_id": None  # 空file_ids（触发跳过mix）
    }
    
    # 场景2：file_ids非空（执行mix_agent）
    test_state_with_file = {
        "input": "请分析我的产检报告",
        "user_type": "孕妇",
        "maternal_id": 1,
        "chat_id": "chat_20250906_002",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file_id": [1001, 1002]  # 非空file_ids（触发执行mix）
    }
    
    # 执行场景1测试（跳过mix）
    logger.info("="*60)
    logger.info("开始测试场景1：file_ids为空（跳过mix_agent）")
    result_empty = graph.invoke(test_state_empty_file)
    logger.info("场景1测试结果：")
    logger.info(f"错误信息：{result_empty['error']}")
    logger.info(f"上下文预览：{result_empty['context'][:200]}..." if result_empty['context'] else "无上下文")
    logger.info(f"最终输出：{result_empty['output']}")
    
    # # 执行场景2测试（执行mix）
    # logger.info("\n" + "="*60)
    # logger.info("开始测试场景2：file_ids非空（执行mix_agent）")
    # result_with_file = graph.invoke(test_state_with_file)
    # logger.info("场景2测试结果：")
    # logger.info(f"错误信息：{result_with_file['error']}")
    # logger.info(f"文件内容预览：{result_with_file['file_content'][:200]}..." if result_with_file['file_content'] else "无文件内容")
    # logger.info(f"最终输出：{result_with_file['output']}")
