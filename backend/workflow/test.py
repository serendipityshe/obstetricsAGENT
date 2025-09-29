import sys
from pathlib import Path
from typing import Annotated, TypedDict, List, Optional, Tuple, Dict
import datetime
import json
import os
import time

root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

from langgraph.graph import StateGraph, END, START
from backend.agents import gen_synth_agent, mix_agent, create_retr_agent
from backend.agents.MeMAgent.core import create_enhanced_mem_agent
from backend.api.v1.services.maternal_service import MaternalService
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class PrengantStateRequired(TypedDict):
    """孕妇状态的必需字段"""
    input: Annotated[str, '用户输入']
    maternal_id: Annotated[int, '孕妇id(必填)']
    chat_id: Annotated[str, '聊天id(必填)']
    user_type: Annotated[str, '用户类型(必填)']
    timestamp: Annotated[str, '时间戳（格式：YYYY-MM-DD HH:MM:SS UTC，必填）']

class PrengantState(PrengantStateRequired, total=False):
    """孕妇状态（支持多轮对话记忆功能）"""
    output: Annotated[str, '模型输出']
    context: Annotated[Optional[str], '上下文（拼接后的字符串）']
    retrieval_professor: Annotated[Optional[List[dict]], '专家知识库检索结果']
    retrieval_pregnant: Annotated[Optional[List[dict]], '孕妇知识库检索结果']

    file_id: Annotated[Optional[List[str]], "文件路径"]
    image_path: Annotated[Optional[str], '图片路径']
    doc_path: Annotated[Optional[str], '文档路径']
    file_content: Annotated[Optional[str], '文件内容']

    error: Annotated[Optional[str], '错误信息']
    memory: Annotated[Optional[List[dict]], '记忆']
    
    # 多轮对话相关字段
    chat_history: Annotated[Optional[List[Dict[str, str]]], '对话历史（结构化）']
    chat_history_text: Annotated[Optional[str], '对话历史（文本形式）']
    compressed_memory: Annotated[Optional[str], '压缩后的记忆']
    memory_summary: Annotated[Optional[str], '记忆摘要']
    
def _get_file_path(file_ids: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
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


def memory_processing_node(state: PrengantState) -> dict:
    """记忆处理节点 - 使用检索式对话历史"""
    start_time = time.time()
    updates = {}
    try:
        # 使用检索式记忆处理
        from backend.agents.MeMAgent.retrieval_memory import create_retrieval_memory_function

        maternal_id = state.get("maternal_id")
        chat_id = state.get("chat_id")
        current_input = state.get("input", "")

        logger.info("启动检索式记忆智能体，基于当前输入检索相关历史")
        invoke_start_time = time.time()

        process_memory = create_retrieval_memory_function()
        mem_result = process_memory(maternal_id, chat_id, current_input)

        invoke_duration = time.time() - invoke_start_time

        # 提取检索式记忆结果
        updates["relevant_history"] = mem_result.get("relevant_history", "")
        updates["history_summary"] = mem_result.get("history_summary", "")

        # 保持向后兼容性
        updates["compressed_memory"] = mem_result.get("relevant_history", "")
        updates["memory_summary"] = mem_result.get("history_summary", "")

        if mem_result.get("error"):
            logger.warning(f"检索式记忆处理有警告: {mem_result['error']}")

        duration = time.time() - start_time
        logger.info(f"检索式记忆处理完成: {mem_result.get('history_summary', 'Unknown')}, 耗时: {duration:.2f}秒 (检索调用: {invoke_duration:.2f}秒)")

    except Exception as e:
        error_msg = f"检索式记忆处理节点执行失败: {str(e)}"
        logger.error(error_msg)
        updates["error"] = error_msg
        updates["relevant_history"] = ""
        updates["history_summary"] = "检索式记忆处理失败"
        updates["compressed_memory"] = ""
        updates["memory_summary"] = "检索式记忆处理失败"

    return updates

def mix_node(state: PrengantState) -> dict:
    """混合智能体节点（补充maternal_id参数传递）"""
    start_time = time.time()
    updates = {}
    try:
        file_ids = state.get("file_id")
        # 修正：检查file_ids是否为None
        if not file_ids:
            updates["image_path"] = None
            updates["doc_path"] = None
            updates["file_content"] = None
            return updates
        
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
        # 修复：确保mix_input符合MixAgentState类型定义
        from backend.agents.MixAgent.core import MixAgentState
        mix_input: MixAgentState = {
            "input": user_input,
            "img_file_path": image_path,
            "doc_file_path": doc_path,
        }
        logger.info("启动混合智能体，开始融合用户输入与文件内容")
        invoke_start_time = time.time()
        mix_result = mix_agent_instance.invoke(mix_input)
        invoke_duration = time.time() - invoke_start_time
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
            dialogues = [dialogues] if dialogues else []

        if not dialogues:
            logger.warning(f"未查询到孕妇{maternal_id}的对话记录。默认使用空字符串")
            return ""
        
        # 修正：ORM对象用属性访问（非字典get），适配服务层返回格式
        first_dialogue = dialogues[0]
        if isinstance(first_dialogue, dict):
            vector_db_path = first_dialogue.get('vector_store_path')
        else:
            # 如果是 ORM 对象
            vector_db_path = getattr(first_dialogue, 'vector_store_path', None)
            
        if not vector_db_path:
            logger.warning(f"孕妇{maternal_id}的对话记录中无向量数据库路径，默认使用空字符串")
            return ""
        return vector_db_path
    except Exception as e:
        error_msg = f"获取向量数据库路径失败：{str(e)}"
        logger.error(error_msg)
        # 不再抛出异常，返回空字符串以避免中断整个流程
        return ""

def retr_node(state: PrengantState) -> dict:
    """检索节点（无新增修改，依赖_get_vector_path修复）"""
    start_time = time.time()
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
        # 修复：确保retr_input符合RetrAgentState类型定义
        from backend.agents.RetrAgent.core import RetrAgentState
        retr_input: RetrAgentState = {
            "input": state.get("input") or "",
            "vector_db_professor": vector_db_professor,
            "vector_db_pregnant": vector_db_path_pregnant,
        }
        retr_result = retr_agent_instance.invoke(retr_input)
        logger.info("检索智能体调用完成，开始校验结果")
        output_data = retr_result.get("output", {})
        print(type(output_data))
        print("output: ", output_data)
        
        # 修复：处理None值情况
        if not output_data or not isinstance(output_data, dict):
            logger.warning("检索智能体返回了无效结果")
            updates["retrieval_professor"] = []
            updates["retrieval_pregnant"] = []
            return updates
            
        retrieval_professor = output_data.get("专家知识库", [])
        retrieval_pregnant = output_data.get("孕妇知识库", [])

        if not retrieval_professor:
            logger.warning(f"专家知识库检索结果为空，可能影响专业建议质量（maternal_id: {maternal_id}）")
        if not retrieval_pregnant:
            logger.warning(
                f"孕妇{maternal_id}的个人知识库检索结果为空，无法提供个性化建议"
            )
        updates["retrieval_professor"] = retrieval_professor
        updates["retrieval_pregnant"] = retrieval_pregnant
        logger.info(f"检索智能体处理成功：检索到{len(retrieval_professor)}条专家知识库结果，{len(retrieval_pregnant)}条孕妇知识库结果")
    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"检索节点执行失败：{str(e)}"
        logger.error(f"{error_msg}, 耗时: {duration:.2f}秒")
        updates["error"] = error_msg
        updates["retrieval_professor"] = []
        updates["retrieval_pregnant"] = []
    return updates

def proc_context(state: PrengantState) -> PrengantState:
    """处理上下文（医学场景优化版：专家知识库优先+长度限制）"""
    start_time = time.time()
    try:
        # 设置上下文最大长度限制（约6000字符，确保AI模型处理速度）
        MAX_CONTEXT_LENGTH = 6000

        file_content = state.get("file_content") or ""
        compressed_memory = state.get("compressed_memory") or ""

        # 检索结果转为字符串（避免None导致拼接报错）
        retrieval_professor_str = str(state.get("retrieval_professor", []))
        retrieval_pregnant_str = str(state.get("retrieval_pregnant", []))

        # 医学场景优先级：专家知识库 > 相关历史 > 文件内容 > 孕妇知识库
        context_parts = []
        current_length = 0

        # 1. 专家知识库（优先级最高，医学权威性）
        if retrieval_professor_str and retrieval_professor_str != "[]":
            professor_part = f"【专家知识库】\n{retrieval_professor_str}"
            # 专家知识库分配最多4000字符
            if len(professor_part) > 4000:
                truncated_professor = retrieval_professor_str[:3960] + "...[专家知识库已截断]"
                professor_part = f"【专家知识库】\n{truncated_professor}"

            context_parts.append(professor_part)
            current_length += len(professor_part)

        # 2. 相关对话历史（次优先级）
        if compressed_memory and current_length < MAX_CONTEXT_LENGTH:
            memory_part = f"【相关历史】\n{compressed_memory}"
            if current_length + len(memory_part) <= MAX_CONTEXT_LENGTH:
                context_parts.append(memory_part)
                current_length += len(memory_part)
            else:
                # 截断对话历史
                available_length = MAX_CONTEXT_LENGTH - current_length - 30
                if available_length > 100:
                    truncated_memory = compressed_memory[:available_length] + "...[历史已截断]"
                    context_parts.append(f"【相关历史】\n{truncated_memory}")
                    current_length = MAX_CONTEXT_LENGTH

        # 3. 文件内容（第三优先级）
        if file_content and current_length < MAX_CONTEXT_LENGTH:
            file_part = f"【文件内容】\n{file_content}"
            if current_length + len(file_part) <= MAX_CONTEXT_LENGTH:
                context_parts.append(file_part)
                current_length += len(file_part)
            else:
                # 截断文件内容
                available_length = MAX_CONTEXT_LENGTH - current_length - 30
                if available_length > 100:
                    truncated_file = file_content[:available_length] + "...[文件已截断]"
                    context_parts.append(f"【文件内容】\n{truncated_file}")
                    current_length = MAX_CONTEXT_LENGTH

        # 4. 孕妇知识库（最低优先级，如果还有空间）
        if retrieval_pregnant_str and retrieval_pregnant_str != "[]" and current_length < MAX_CONTEXT_LENGTH:
            pregnant_part = f"【个人知识库】\n{retrieval_pregnant_str}"
            if current_length + len(pregnant_part) <= MAX_CONTEXT_LENGTH:
                context_parts.append(pregnant_part)
                current_length += len(pregnant_part)
            else:
                # 截断个人知识库
                available_length = MAX_CONTEXT_LENGTH - current_length - 30
                if available_length > 100:
                    truncated_pregnant = retrieval_pregnant_str[:available_length] + "...[个人库已截断]"
                    context_parts.append(f"【个人知识库】\n{truncated_pregnant}")

        context = "\n\n".join(context_parts)
        state["context"] = context
        duration = time.time() - start_time

        logger.info(f"医学上下文处理完成，总长度：{len(context)}字符（限制：{MAX_CONTEXT_LENGTH}），包含{len(context_parts)}个部分, 耗时: {duration:.2f}秒")

    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"处理上下文节点执行失败：{str(e)}"
        logger.error(f"{error_msg}, 耗时: {duration:.2f}秒")
        state["error"] = error_msg
        state["context"] = None
    return state

def gen_synth_node(state: PrengantState) -> PrengantState:
    """生成合成智能体节点（无修改）"""
    start_time = time.time()
    try:
        gen_synth_agent_instance = gen_synth_agent()
        # 修复：确保gen_synth_input符合GenSynthAgentState类型定义
        from backend.agents.GenSynthAgent.core import GenSynthAgentState
        context = state.get("context") or ""  # 处理None值
        gen_synth_input: GenSynthAgentState = {
            "input": state.get("input") or "",
            "user_type": state.get("user_type") or "",
            "context": context,
            "output": "",  # 添加必需字段
            "error": None,   # 添加可选字段
        }
        logger.info("启动合成智能体，开始生成合成输出")
        invoke_start_time = time.time()
        gen_synth_result = gen_synth_agent_instance.invoke(gen_synth_input)
        invoke_duration = time.time() - invoke_start_time
        state["output"] = gen_synth_result.get("output") or ""
        output_str = state['output']
        duration = time.time() - start_time
        logger.info(f"合成智能体处理成功：生成输出={output_str[:50] if output_str else ''}…, 耗时: {duration:.2f}秒 (agent调用: {invoke_duration:.2f}秒)")  # 截断长输出避免日志冗余
    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"合成节点执行失败：{str(e)}"
        logger.error(f"{error_msg}, 耗时: {duration:.2f}秒")
        state["error"] = error_msg
        state["output"] = ""
    return state

# 新增：流式版本的孕妇工作流
async def prengant_workflow_stream(state: PrengantState):
    """
    异步流式孕妇工作流 - 保持专家知识库质量，解决多用户并发阻塞
    将所有检索操作异步化，支持真正的高并发
    """
    try:
        # 使用线程池异步化所有阻塞操作
        from concurrent.futures import ThreadPoolExecutor
        import asyncio

        # 创建专用线程池（如果不存在）
        if not hasattr(prengant_workflow_stream, '_thread_pool'):
            prengant_workflow_stream._thread_pool = ThreadPoolExecutor(
                max_workers=20,
                thread_name_prefix="workflow_async_"
            )

        thread_pool = prengant_workflow_stream._thread_pool

        # 1. 异步并行处理：记忆、文件处理和检索
        async def async_memory_processing():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(thread_pool, memory_processing_node, state)

        async def async_file_processing():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(thread_pool, mix_node, state)

        async def async_retrieval_processing():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(thread_pool, retr_node, state)

        # 并行执行所有处理步骤（不阻塞事件循环）
        memory_result, file_result, retrieval_result = await asyncio.gather(
            async_memory_processing(),
            async_file_processing(),
            async_retrieval_processing(),
            return_exceptions=True
        )

        # 2. 整合结果
        if not isinstance(memory_result, Exception):
            state.update(memory_result)

        if not isinstance(file_result, Exception):
            state.update(file_result)

        if not isinstance(retrieval_result, Exception):
            state.update(retrieval_result)

        # 3. 异步上下文整合
        async def async_context_processing():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(thread_pool, proc_context, state)

        state = await async_context_processing()

        # 4. 流式生成回答（基于完整的专家知识）
        from backend.agents.GenSynthAgent.core import gen_synth_node_stream, GenSynthAgentState

        # 构造生成智能体的输入
        context = state.get("context") or ""
        gen_synth_input: GenSynthAgentState = {
            "input": state.get("input") or "",
            "user_type": state.get("user_type") or "",
            "context": context,
            "output": "",
            "error": None,
        }

        # 流式生成并yield每个chunk（基于专家知识库检索结果）
        async for chunk in gen_synth_node_stream(gen_synth_input):
            yield chunk

    except Exception as e:
        yield f"\n\n❌ 工作流执行失败：{str(e)}"

def prengant_workflow():
    """孕妇工作流（集成增强版记忆智能体）"""
    builder = StateGraph(PrengantState)
    
    # 添加节点
    builder.add_node("memory_processing", memory_processing_node)  # 使用MeMAgent处理记忆
    builder.add_node("mix", mix_node)
    builder.add_node("retr", retr_node)
    builder.add_node("proc_context", proc_context)
    builder.add_node("gen_synth", gen_synth_node)

    # 构建工作流：记忆处理 → 并行处理（文件处理+检索） → 上下文整合 → 生成回答
    builder.add_edge(START, "memory_processing")
    builder.add_edge("memory_processing", "mix")
    builder.add_edge("memory_processing", "retr")
    builder.add_edge("mix", "proc_context")
    builder.add_edge("retr", "proc_context")
    builder.add_edge("proc_context", "gen_synth")
    builder.add_edge("gen_synth", END)

    graph = builder.compile()
    return graph

if __name__ == "__main__":
    graph = prengant_workflow()
    # 构造完整的输入参数（含必填字段），确保符合PrengantState类型
    input_data: PrengantState = {
        "input": "我之前问过头晕的问题，现在想了解一下孕期饮食建议",
        "user_type": "pregnant_mother",
        "maternal_id": 2,
        "chat_id": "chat_2_pregnant_mother_94ecb7d2-2060-48b5-b250-6a7f2ef0da36",  # 使用已创建的测试chat_id
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file_id": []  # 测试多轮对话，不使用文件
    }
    
    # 执行工作流并打印结果
    result = graph.invoke(input_data)
    logger.info("="*50)
    logger.info("增强版多轮对话工作流执行结果：")
    logger.info(f"错误信息：{result.get('error') or '无'}")
    logger.info(f"生成输出：{result.get('output') or '无'}")
    logger.info(f"记忆摘要：{result.get('memory_summary') or '无'}")
    
    context_str = result.get('context')
    if context_str:
        logger.info(f"上下文长度：{len(context_str)}")
        # 显示前200字符作为预览
        logger.info(f"上下文预览：{context_str[:200]}...")
    else:
        logger.info("上下文：无")