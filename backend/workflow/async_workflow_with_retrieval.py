"""
异步化工作流 - 保持专家知识库质量，解决多用户并发阻塞
将同步检索操作改为异步，支持真正的高并发
"""
import asyncio
import time
import json
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, Any
import logging
from concurrent.futures import ThreadPoolExecutor

from backend.workflow.test import PrengantState
from backend.api.v1.services.maternal_service import MaternalService

logger = logging.getLogger(__name__)

# 专用线程池用于检索操作，避免阻塞事件循环
RETRIEVAL_THREAD_POOL = ThreadPoolExecutor(
    max_workers=20,  # 支持20个并发检索
    thread_name_prefix="retrieval_"
)

class AsyncWorkflowWithRetrieval:
    """异步化工作流引擎 - 保持检索质量，解决并发阻塞"""

    def __init__(self):
        self.maternal_service = MaternalService()

    async def execute_async_workflow_stream(self, state: PrengantState) -> AsyncGenerator[str, None]:
        """
        异步化工作流流式执行
        策略：所有检索操作异步化，不阻塞事件循环，支持真正高并发
        """
        start_time = time.time()
        request_id = f"req_{uuid.uuid4().hex[:8]}"

        try:
            # 立即发送开始消息
            yield self._create_message("start", "🚀 开始智能诊疗分析...", 0)

            # 异步并行执行所有处理步骤
            yield self._create_message("progress", "🔍 正在检索专家知识库...", 10)

            # 并行执行记忆、文件、检索处理（全部异步化）
            memory_task = self._async_memory_processing(state)
            file_task = self._async_file_processing(state)
            retrieval_task = self._async_retrieval_processing(state)

            yield self._create_message("progress", "🧠 AI医生正在分析多源医疗知识...", 25)

            # 等待所有处理完成，但不阻塞其他用户
            memory_result, file_result, retrieval_result = await asyncio.gather(
                memory_task, file_task, retrieval_task, return_exceptions=True
            )

            yield self._create_message("progress", "📚 知识整合完成，开始生成专业建议...", 50)

            # 处理结果
            workflow_state = state.copy()

            # 整合记忆结果
            if not isinstance(memory_result, Exception):
                workflow_state.update(memory_result)

            # 整合文件结果
            if not isinstance(file_result, Exception):
                workflow_state.update(file_result)

            # 整合检索结果
            if not isinstance(retrieval_result, Exception):
                workflow_state.update(retrieval_result)

            # 上下文处理（异步化）
            context_result = await self._async_context_processing(workflow_state)
            workflow_state.update(context_result)

            yield self._create_message("progress", "🤖 基于专家知识开始流式生成...", 70)

            # 流式生成AI回答（基于完整的专家知识）
            chunk_count = 0
            full_response = ""

            async for ai_chunk in self._stream_ai_with_expert_knowledge(workflow_state, request_id):
                chunk_count += 1
                full_response += ai_chunk

                # 实时发送AI内容
                yield self._create_message("ai_content", "", 0, content=ai_chunk, chunk_id=chunk_count)

                # 定期发送进度
                if chunk_count % 15 == 0:
                    progress = min(70 + chunk_count // 3, 95)
                    yield self._create_message("progress", f"💭 基于专家知识生成中... ({chunk_count} tokens)", progress)

            # 计算总耗时
            total_time = time.time() - start_time
            yield self._create_message("progress", f"✅ 专家级回答完成 (耗时 {total_time:.1f}秒，共 {chunk_count} tokens)", 95)

            # 构造最终响应数据
            response_data = await self._build_response_data(state, full_response, total_time)
            yield self._create_message("complete", f"🎉 基于专家知识的诊疗建议已完成", 100, data=response_data)
            yield self._create_message("done")

        except Exception as e:
            logger.error(f"[{request_id}] 异步工作流失败: {e}")
            yield self._create_message("error", f"❌ 处理失败: {str(e)}")
            yield self._create_message("done")

    async def _async_memory_processing(self, state: PrengantState) -> Dict[str, Any]:
        """异步记忆处理 - 不阻塞事件循环"""
        def sync_memory_processing():
            from backend.workflow.test import memory_processing_node
            return memory_processing_node(state)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(RETRIEVAL_THREAD_POOL, sync_memory_processing)

    async def _async_file_processing(self, state: PrengantState) -> Dict[str, Any]:
        """异步文件处理 - 不阻塞事件循环"""
        def sync_file_processing():
            from backend.workflow.test import mix_node
            return mix_node(state)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(RETRIEVAL_THREAD_POOL, sync_file_processing)

    async def _async_retrieval_processing(self, state: PrengantState) -> Dict[str, Any]:
        """异步检索处理 - 最重要的优化点"""
        def sync_retrieval_processing():
            from backend.workflow.test import retr_node
            return retr_node(state)

        loop = asyncio.get_event_loop()
        # 使用专用线程池，避免阻塞其他用户的请求
        return await loop.run_in_executor(RETRIEVAL_THREAD_POOL, sync_retrieval_processing)

    async def _async_context_processing(self, state: PrengantState) -> Dict[str, Any]:
        """异步上下文处理"""
        def sync_context_processing():
            from backend.workflow.test import proc_context
            result_state = proc_context(state)
            # proc_context返回的是完整state，我们只取新增的部分
            return {"context": result_state.get("context", "")}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(RETRIEVAL_THREAD_POOL, sync_context_processing)

    async def _stream_ai_with_expert_knowledge(self, state: PrengantState, request_id: str) -> AsyncGenerator[str, None]:
        """基于专家知识进行流式AI生成"""
        try:
            # 构造增强的医疗提示词（包含检索到的专家知识）
            enhanced_prompt = self._create_expert_medical_prompt(state)

            # 获取模型配置
            model_config = await self._get_model_config()

            # 流式调用AI（基于完整的专家知识）
            from backend.agents.tools.tools import qwen_tool_stream

            async for ai_chunk in qwen_tool_stream(
                input=enhanced_prompt,
                img_path='',
                model_name=model_config["llm_model"],
                api_key=model_config["api_key"],
                base_url=model_config["base_url"],
                temperature=model_config["temperature"]
            ):
                yield ai_chunk

        except Exception as e:
            logger.error(f"[{request_id}] 专家知识AI生成失败: {e}")
            yield f"\n\n❌ AI生成失败：{str(e)}"

    def _create_expert_medical_prompt(self, state: PrengantState) -> str:
        """创建基于专家知识的医疗提示词"""
        user_input = state.get("input", "")
        user_type = state.get("user_type", "pregnant_mother")

        # 获取检索到的专家知识
        retrieval_professor = state.get("retrieval_professor", [])
        retrieval_pregnant = state.get("retrieval_pregnant", [])
        compressed_memory = state.get("compressed_memory", "")
        file_content = state.get("file_content", "")
        context = state.get("context", "")

        # 构建增强提示词
        prompt_parts = [
            "你是一位专业的妇产科医生和孕期健康顾问。请基于以下专家知识库和用户信息，为孕妇提供准确、温暖、专业的医疗建议。",
            f"\n用户类型：{user_type}",
            f"用户问题：{user_input}",
        ]

        # 添加专家知识库检索结果
        if retrieval_professor:
            prompt_parts.append(f"\n【专家知识库】：\n{str(retrieval_professor[:3])}")  # 取前3条最相关

        # 添加个人知识库检索结果
        if retrieval_pregnant:
            prompt_parts.append(f"\n【个人医疗历史】：\n{str(retrieval_pregnant[:2])}")  # 取前2条

        # 添加历史对话记忆
        if compressed_memory:
            prompt_parts.append(f"\n【历史对话摘要】：\n{compressed_memory[:300]}")

        # 添加文件内容
        if file_content:
            prompt_parts.append(f"\n【用户上传文件内容】：\n{file_content[:200]}")

        # 添加整合的上下文
        if context and context not in str(retrieval_professor):
            prompt_parts.append(f"\n【补充医疗信息】：\n{context[:300]}")

        prompt_parts.extend([
            "\n请遵循以下原则：",
            "1. 优先基于上述专家知识库提供建议",
            "2. 使用温暖、专业但易懂的语调",
            "3. 提供基于循证医学的建议",
            "4. 明确指出何时需要就医",
            "5. 给出具体可行的日常护理建议",
            "6. 如果涉及严重症状，务必建议立即就医",
            "7. 回答要全面但简洁，重点突出",
            "\n请现在基于专家知识开始回答："
        ])

        return "\n".join(prompt_parts)

    async def _get_model_config(self) -> Dict[str, Any]:
        """异步获取模型配置"""
        def sync_get_config():
            import yaml
            with open("backend/config/model_settings.yaml", "r", encoding="utf-8") as f:
                model_settings = yaml.safe_load(f)
            return model_settings.get("DEFAULT_MODEL", {})

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_get_config)

    async def _build_response_data(self, state: PrengantState, ai_response: str, duration: float) -> Dict[str, Any]:
        """构建响应数据"""
        from backend.api.v2.routes.chat_routes import PregnantWorkflowRequest, MessageItem, TextContent, ChatMeta, WorkflowData, PregnantWorkflowResponse

        # 构造用户消息
        user_message_id = f"msg_{uuid.uuid4()}"
        user_content = [TextContent(type="text", text=state.get("input", ""))]
        user_message = MessageItem(
            message_id=user_message_id,
            role="user",
            content=user_content,
            timestamp=state.get("timestamp", datetime.now().isoformat())
        )

        # 构造助手消息
        assistant_message_id = f"msg_{uuid.uuid4()}"
        assistant_content = [TextContent(type="text", text=ai_response)]
        assistant_message = MessageItem(
            message_id=assistant_message_id,
            role="assistant",
            content=assistant_content,
            timestamp=datetime.now().isoformat()
        )

        # 构造会话标题
        session_title = state.get("input", "")[:20] + "..." if len(state.get("input", "")) > 20 else state.get("input", "")

        # 构造响应数据
        workflow_data = WorkflowData(
            chat_meta=ChatMeta(
                chat_id=state.get("chat_id", ""),
                user_type=state.get("user_type", ""),
                maternal_id=state.get("maternal_id", 0)
            ),
            session_title=session_title,
            messages=[user_message, assistant_message],
            error=None
        )

        response = PregnantWorkflowResponse(
            code=200,
            msg="success",
            data=workflow_data
        )

        return response.model_dump()

    def _create_message(self, msg_type: str, message: str = "", progress: int = 0, **kwargs) -> str:
        """创建标准化的流式消息"""
        data = {
            "type": msg_type,
            "timestamp": datetime.now().isoformat()
        }

        if message:
            data["message"] = message
        if progress > 0:
            data["progress"] = progress

        # 添加其他参数
        data.update(kwargs)

        return json.dumps(data, ensure_ascii=False) + "\n"


# 主要的异步流式工作流函数
async def async_workflow_stream_with_retrieval(state: PrengantState) -> AsyncGenerator[str, None]:
    """
    异步化工作流流式执行 - 保持专家知识质量，解决并发阻塞

    特点：
    1. 所有检索操作异步化，支持真正高并发
    2. 保持完整的专家知识库检索流程
    3. 基于专家知识进行AI生成，确保回答质量
    4. 流式返回，用户体验良好
    """
    workflow = AsyncWorkflowWithRetrieval()
    async for chunk in workflow.execute_async_workflow_stream(state):
        yield chunk


if __name__ == "__main__":
    # 测试异步工作流
    import asyncio

    async def test_async_workflow():
        test_state: PrengantState = {
            "input": "孕期头晕怎么办？",
            "maternal_id": 1,
            "chat_id": "test_async_retrieval_123",
            "user_type": "pregnant_mother",
            "timestamp": datetime.now().isoformat(),
            "file_id": []
        }

        print("=== 测试异步化检索工作流 ===")
        start_time = time.time()

        async for chunk in async_workflow_stream_with_retrieval(test_state):
            print(f"[{time.time() - start_time:.2f}s] {chunk.strip()}")

    # asyncio.run(test_async_workflow())