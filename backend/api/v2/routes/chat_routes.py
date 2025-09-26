from starlette.responses import JSONResponse
from fastapi import APIRouter, HTTPException, status, Depends, Form, Path, Query, UploadFile, File, Body
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from typing import Any, Optional, List, Union, Literal, AsyncGenerator
from datetime import date, datetime, timedelta

import json
import uuid
import os
import mimetypes
import time
import asyncio
from asyncio import Semaphore, Queue
from backend.workflow.test import prengant_workflow, PrengantState
from backend.api.v1.services.maternal_service import MaternalService  # 复用服务层
# 异步任务管理器相关导入已移除，统一使用流式处理
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock

# 初始化日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("pregnant-workflow-api")

# ==============================
# P0级性能优化配置
# ==============================

# 1. 并发控制配置
MAX_CONCURRENT_REQUESTS = 20  # 最大并发处理数量
WORKFLOW_TIMEOUT = 90.0      # 工作流超时时间(秒)
QUEUE_MAX_SIZE = 50          # 请求队列最大大小

# 2. 全局并发控制信号量
workflow_semaphore = Semaphore(MAX_CONCURRENT_REQUESTS)

# 3. 请求队列
request_queue: Queue = Queue(maxsize=QUEUE_MAX_SIZE)

# 4. 请求队列处理器
async def process_queue_requests():
    """处理请求队列中的任务"""
    while True:
        try:
            # 等待队列中的请求
            request_item = await request_queue.get()
            request_data, response_future = request_item

            # 执行请求
            try:
                result = await execute_workflow_stream_protected(request_data)
                response_future.set_result(result)
            except Exception as e:
                response_future.set_exception(e)
            finally:
                request_queue.task_done()

        except Exception as e:
            logger.error(f"队列处理器异常: {e}")
            await asyncio.sleep(1)  # 防止无限循环

# 启动队列处理器
async def start_queue_processor():
    """启动请求队列处理器"""
    asyncio.create_task(process_queue_requests())

async def wait_for_queue_result(response_future: asyncio.Future):
    """等待队列处理结果并流式返回"""
    try:
        # 等待队列处理完成
        result_generator = await response_future

        # 流式返回结果
        async for chunk in result_generator:
            yield chunk

    except Exception as e:
        logger.error(f"队列结果等待异常：{e}")
        yield f"{json.dumps({'type': 'error', 'message': f'队列处理失败: {str(e)}'}, ensure_ascii=False)}\n"
        yield f"{json.dumps({'type': 'done'}, ensure_ascii=False)}\n"

# 5. 性能监控数据结构
@dataclass
class PerformanceMetrics:
    active_requests: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0
    queue_waiting: int = 0
    avg_response_time: float = 0.0
    recent_response_times: deque = None

    def __post_init__(self):
        if self.recent_response_times is None:
            self.recent_response_times = deque(maxlen=100)

# 6. 全局性能监控实例
performance_metrics = PerformanceMetrics()
metrics_lock = Lock()

def update_metrics(success: bool, duration: float, timeout: bool = False):
    """更新性能指标"""
    with metrics_lock:
        performance_metrics.total_requests += 1
        if success:
            performance_metrics.successful_requests += 1
        else:
            performance_metrics.failed_requests += 1

        if timeout:
            performance_metrics.timeout_requests += 1

        performance_metrics.recent_response_times.append(duration)

        # 计算平均响应时间
        if performance_metrics.recent_response_times:
            performance_metrics.avg_response_time = sum(performance_metrics.recent_response_times) / len(performance_metrics.recent_response_times)

def increment_active_requests():
    """增加活跃请求计数"""
    with metrics_lock:
        performance_metrics.active_requests += 1

def decrement_active_requests():
    """减少活跃请求计数"""
    with metrics_lock:
        performance_metrics.active_requests -= 1

def update_queue_waiting(count: int):
    """更新队列等待数量"""
    with metrics_lock:
        performance_metrics.queue_waiting = count

def get_performance_snapshot():
    """获取性能指标快照"""
    with metrics_lock:
        return {
            "active_requests": performance_metrics.active_requests,
            "total_requests": performance_metrics.total_requests,
            "successful_requests": performance_metrics.successful_requests,
            "failed_requests": performance_metrics.failed_requests,
            "timeout_requests": performance_metrics.timeout_requests,
            "success_rate": f"{(performance_metrics.successful_requests / max(performance_metrics.total_requests, 1)) * 100:.1f}%",
            "avg_response_time": f"{performance_metrics.avg_response_time:.2f}s",
            "queue_waiting": performance_metrics.queue_waiting,
            "queue_size": request_queue.qsize(),
            "semaphore_available": workflow_semaphore._value
        }

# 初始化路由（标签与现有聊天管理服务分类一致）
router = APIRouter(tags=["聊天管理服务"])
maternal_service = MaternalService()

# 初始化标志，确保队列处理器只启动一次
_queue_processor_started = False

async def ensure_queue_processor_started():
    """确保请求队列处理器已启动"""
    global _queue_processor_started
    if not _queue_processor_started:
        await start_queue_processor()
        _queue_processor_started = True
        logger.info("请求队列处理器已启动")

# ------------------------------
# 1. 通用工具函数（辅助生成URL、文件信息等）
# ------------------------------
# 注意：由于返回格式简化为file_id，以下函数已不再使用，保留作为参考
# def generate_temp_token() -> str:
#     """生成临时URL令牌（实际项目需对接文件服务生成有效令牌）"""
#     return str(uuid.uuid4())[:8]  # 取UUID前8位作为临时令牌
# 
# def get_file_size(file_path: str) -> int:
#     """获取文件大小（字节），路径不存在时返回0"""
#     try:
#         return os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0
#     except Exception as e:
#         logger.warning(f"获取文件大小失败: {e}")
#         return 0
# 
# def generate_expire_time(days: int = 7) -> str:
#     """生成文件过期时间（当前时间+N天），格式：YYYY-MM-DD HH:MM:SS"""
#     expire_dt = datetime.now() + timedelta(days=days)
#     return expire_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
# 
# def get_file_name_from_path(file_path: str) -> str:
#     """从文件路径中提取文件名（如无路径则返回默认名）"""
#     if not file_path:
#         return "unknown_file"
#     return os.path.basename(file_path) or "unknown_file"
# 
# def get_file_type_from_path(file_path: str) -> str:
#     """从文件路径推断MIME类型（简化版，实际项目需用专业库如python-magic）"""
#     if not file_path:
#         return "application/octet-stream"
#     ext = os.path.splitext(file_path)[-1].lower()
#     if ext in [".jpg", ".jpeg", ".png", ".gif"]:
#         return f"image/{ext[1:]}"
#     elif ext == ".pdf":
#         return "application/pdf"
#     elif ext in [".doc", ".docx"]:
#         return "application/msword" if ext == ".doc" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
#     else:
#         return "application/octet-stream"

# ------------------------------
# 2. 创建chat_id的接口
# ------------------------------
class CreateChatIdJsonRequest(BaseModel):
    """创建对话ID的JSON请求模型"""
    maternal_id: int = Field(..., description="孕妇唯一标识ID（必填，用于关联个人数据）")
    user_type: str = Field(..., description="用户类型（必填，固定值：pregnant_mother/doctor）")
    
    # 可选：添加验证确保user_type只能是指定值
    @classmethod
    def validate_user_type(cls, v):
        if v not in ["pregnant_mother", "doctor"]:
            raise ValueError("user_type必须是'pregnant_mother'或'doctor'")
        return v

class CreateChatIdRequest(BaseModel):
    """创建对话ID的响应模型"""
    code: int = Field(..., description="状态码：200=成功，500=系统错误")
    msg: str = Field(..., description="提示信息")
    data: Optional[dict] = Field(None, description="业务数据，包含生成的chat_id")

@router.post(
    "/chat_id",
    description="创建对话id",
    response_model=CreateChatIdRequest,
    status_code=status.HTTP_200_OK
)
async def create_chat_id(
    request: CreateChatIdJsonRequest
):
    try:
        chat_uuid = str(uuid.uuid4())
        chat_id = f'chat_{request.maternal_id}_{request.user_type}_{chat_uuid}'
        save_chat_path = os.path.join('dataset', 'pregnant_mother', str(request.maternal_id), 'chat')
        os.makedirs(save_chat_path, exist_ok=True)
        json_file_path = os.path.join(save_chat_path, f'{chat_id}.json')
        
        # 生成向量存储路径
        vector_store_path = f"/root/project2/data/vector_store/chat_{chat_id}_maternal_{request.maternal_id}"
        
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump({}, f)  # 写入空 JSON 对象，保证文件格式正确
            print(f"空 JSON 文件已创建: {json_file_path}")
            
            # 创建聊天记录并同时设置向量存储路径
            result = maternal_service.dataset_service.create_dialogue(
                maternal_id=request.maternal_id,
                chat_id=chat_id,
                dialogue_content=json_file_path,
                vector_store_path=vector_store_path
            )
            logger.info(f"已为 chat_id={chat_id} 初始化向量存储路径: {vector_store_path}")
            
        except Exception as e:
            print(f"创建空 JSON 文件或数据库记录失败: {str(e)}")
        return CreateChatIdRequest(
            code=200,
            msg="对话ID创建成功",
            data={"chat_id": chat_id, "vector_store_path": vector_store_path}
        )
    except Exception as e:
        logger.error(f"创建对话ID失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=CreateChatIdRequest(
                code=500,
                msg="创建对话ID失败",
                data=None
            ).model_dump()
        )


# ------------------------------
# 3. 定义请求/响应模型（Pydantic验证）
# ------------------------------
# 3.1 消息内容子模型（支持text/image_url/document三种类型）
class TextContent(BaseModel):
    """文本类型消息内容"""
    type: Literal["text"] = Field("text", description="内容类型：固定为text")
    text: str = Field(..., description="文本内容")

class ImageUrlInfo(BaseModel):
    """图片URL信息"""
    file_id: str = Field(..., description="文件ID")

class ImageUrlContent(BaseModel):
    """图片类型消息内容"""
    type: Literal["image_url"] = Field("image_url", description="内容类型：固定为image_url")
    image_url: ImageUrlInfo = Field(..., description="图片详细信息")

class DocumentInfo(BaseModel):
    """文档URL信息"""
    file_id: str = Field(..., description="文件ID")

class DocumentContent(BaseModel):
    """文档类型消息内容"""
    type: Literal["document"] = Field("document", description="内容类型：固定为document")
    document: DocumentInfo = Field(..., description="文档详细信息")

# 消息内容类型集合（Union）
MessageContent = Union[TextContent, ImageUrlContent, DocumentContent]

# 3.2 单条消息模型
class MessageItem(BaseModel):
    """单条对话消息模型（用户/助手）"""
    message_id: str = Field(..., description="消息唯一ID（格式：msg_+UUID）")
    role: str = Field(..., description="角色：user（用户）/assistant（助手）")
    content: List[MessageContent] = Field(..., description="消息内容列表（支持多类型混合）")
    timestamp: str = Field(..., description="消息时间戳（格式：YYYY-MM-DD HH:MM:SS）")

# 3.3 对话元数据模型
class ChatMeta(BaseModel):
    """对话元数据（标识对话归属）"""
    chat_id: str = Field(..., description="对话ID（与创建接口返回一致）")
    user_type: str = Field(..., description="用户类型（pregnant_mother/doctor）")
    maternal_id: int = Field(..., description="孕妇唯一标识ID")

# 3.4 接口响应数据模型（data字段内部结构）
class WorkflowData(BaseModel):
    """对话接口响应的业务数据模型"""
    chat_meta: ChatMeta = Field(..., description="对话元数据")
    session_title: str = Field(..., description="会话标题（取自用户首次输入）")
    messages: List[MessageItem] = Field(..., description="对话消息列表（用户+助手）")
    error: Optional[str] = Field(None, description="错误信息（无错误时为null）")

# 3.5 接口请求模型（保留原字段，优化描述）
class PregnantWorkflowRequest(BaseModel):
    """孕妇工作流调用请求模型"""
    input: str = Field(..., description="用户输入的问题/需求（如：孕妇最近出现头晕症状，需要什么建议？）")
    maternal_id: int = Field(..., description="孕妇唯一标识ID（必填，用于关联个人数据）")
    chat_id: str = Field(..., description="聊天会话ID（必填，与创建接口返回一致）")
    user_type: str = Field(..., description="用户类型（必填，固定值：pregnant_mother/doctor）")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        description="请求时间戳（格式：YYYY-MM-DD HH:MM:SS，默认自动生成）"
    )
    file_id: Optional[List[str]] = Field(None, description="关联文件ID列表（支持图片/文档）")

# 3.6 接口最终响应模型（完全匹配目标格式）
class PregnantWorkflowResponse(BaseModel):
    """孕妇工作流调用最终响应模型"""
    code: int = Field(..., description="状态码：200=成功，500=失败")
    msg: str = Field(..., description="状态描述：success/失败原因")
    data: WorkflowData = Field(..., description="业务数据（含对话内容）")

# 异步任务相关模型已移除，统一使用流式响应

# ------------------------------
# 4. 工作流执行函数（流式版本）
# ------------------------------

# 同步工作流函数已移除，统一使用流式处理模式

# ------------------------------
# 流式工作流执行函数
# ------------------------------

async def execute_workflow_stream_protected(request_data: dict) -> AsyncGenerator[str, None]:
    """带并发控制和超时保护的流式工作流执行"""
    request_start_time = time.time()
    request_id = f"req_{uuid.uuid4().hex[:8]}"

    # 增加活跃请求计数
    increment_active_requests()

    # 记录请求开始
    logger.info(f"[{request_id}] 开始处理请求 - 当前活跃请求: {performance_metrics.active_requests}")

    try:
        # 1. 获取信号量（并发控制）
        logger.info(f"[{request_id}] 等待获取信号量 - 可用数量: {workflow_semaphore._value}")
        async with workflow_semaphore:
            logger.info(f"[{request_id}] 已获取信号量，开始处理")

            # 2. 超时保护 - 使用简化的超时处理
            try:
                # 记录开始时间用于超时检测
                start_time = time.time()

                # 执行工作流生成器
                async for chunk in execute_workflow_stream_internal(request_data, request_id):
                    # 检查是否超时
                    if time.time() - start_time > WORKFLOW_TIMEOUT:
                        logger.error(f"[{request_id}] 工作流执行超时")
                        raise asyncio.TimeoutError("工作流执行超时")

                    yield chunk

                # 成功完成
                duration = time.time() - request_start_time
                update_metrics(success=True, duration=duration)
                logger.info(f"[{request_id}] 请求成功完成，耗时: {duration:.2f}s")

            except asyncio.TimeoutError:
                # 超时处理
                duration = time.time() - request_start_time
                update_metrics(success=False, duration=duration, timeout=True)
                logger.error(f"[{request_id}] 请求超时，耗时: {duration:.2f}s")

                yield f"{json.dumps({'type': 'error', 'message': f'⏰ 处理超时（{WORKFLOW_TIMEOUT}秒），请稍后重试', 'progress': 0}, ensure_ascii=False)}\n"
                yield f"{json.dumps({'type': 'done'}, ensure_ascii=False)}\n"

    except Exception as e:
        # 其他异常处理
        duration = time.time() - request_start_time
        update_metrics(success=False, duration=duration)
        logger.error(f"[{request_id}] 请求处理异常: {str(e)}", exc_info=True)

        yield f"{json.dumps({'type': 'error', 'message': f'❌ 处理失败: {str(e)}', 'progress': 0}, ensure_ascii=False)}\n"
        yield f"{json.dumps({'type': 'done'}, ensure_ascii=False)}\n"

    finally:
        # 减少活跃请求计数
        decrement_active_requests()
        logger.info(f"[{request_id}] 请求处理完成 - 当前活跃请求: {performance_metrics.active_requests}")

        # 记录详细的性能日志
        perf_snapshot = get_performance_snapshot()
        logger.info(f"[{request_id}] 性能快照 - 成功率: {perf_snapshot['success_rate']}, "
                   f"平均响应时间: {perf_snapshot['avg_response_time']}, "
                   f"可用信号量: {perf_snapshot['semaphore_available']}, "
                   f"队列大小: {perf_snapshot['queue_size']}")

async def execute_workflow_stream_internal(request_data: dict, request_id: str) -> AsyncGenerator[str, None]:
    """内部工作流执行逻辑（原execute_workflow_stream的核心逻辑）"""
    try:
        request = PregnantWorkflowRequest(**request_data)
        start_time = time.time()

        # 发送开始消息
        logger.info(f"[{request_id}] 发送开始消息 - 输入长度: {len(request.input)}")
        yield f"{json.dumps({'type': 'start', 'message': '🚀 开始处理您的问题...', 'timestamp': datetime.now().isoformat(), 'progress': 0}, ensure_ascii=False)}\n"

        # 等待一小段时间，让前端能看到开始消息
        await asyncio.sleep(0.1)

        # 发送进度消息（增加更详细的监控信息）
        perf_snapshot = get_performance_snapshot()
        logger.info(f"[{request_id}] 工作流初始化 - 当前并发: {perf_snapshot['active_requests']}, "
                   f"可用信号量: {perf_snapshot['semaphore_available']}, "
                   f"队列大小: {perf_snapshot['queue_size']}")
        progress_msg = f"📋 正在初始化智能医疗工作流... (当前并发: {perf_snapshot['active_requests']})"
        yield f"{json.dumps({'type': 'progress', 'message': progress_msg, 'progress': 5}, ensure_ascii=False)}\n"

        # 构造用户消息
        user_message_id = f"msg_{uuid.uuid4()}"
        user_content: List[MessageContent] = [TextContent(type="text", text=request.input)]

        # 处理文件
        if request.file_id:
            yield f"{json.dumps({'type': 'progress', 'message': f'📁 正在分析您上传的 {len(request.file_id)} 个医疗文件...', 'progress': 15}, ensure_ascii=False)}\n"

            for i, file_id_str in enumerate(request.file_id):
                try:
                    file_info = maternal_service.get_medical_file_by_fileid(file_id_str)
                    if file_info:
                        file_name = file_info.get("file_name", "未知文件")
                        file_type = file_info.get("file_type", "").lower()

                        yield f"{json.dumps({'type': 'progress', 'message': f'📄 正在解析文件: {file_name}', 'progress': 15 + (i+1) * 5}, ensure_ascii=False)}\n"

                        if (file_type.startswith("image/") or
                            file_type in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]):
                            user_content.append(ImageUrlContent(
                                type="image_url",
                                image_url=ImageUrlInfo(file_id=file_id_str)
                            ))
                        else:
                            user_content.append(DocumentContent(
                                type="document",
                                document=DocumentInfo(file_id=file_id_str)
                            ))
                except Exception as e:
                    logger.error(f"处理文件ID {file_id_str} 时出错: {str(e)}")
                    yield f"{json.dumps({'type': 'progress', 'message': f'⚠️ 文件处理失败，继续处理其他内容...', 'progress': 15 + (i+1) * 5}, ensure_ascii=False)}\n"
                    continue

        user_message = MessageItem(
            message_id=user_message_id,
            role="user",
            content=user_content,
            timestamp=request.timestamp
        )

        # 执行工作流
        yield f"{json.dumps({'type': 'progress', 'message': '🤖 正在启动AI智能诊疗系统...', 'progress': 35}, ensure_ascii=False)}\n"
        await asyncio.sleep(0.2)

        yield f"{json.dumps({'type': 'progress', 'message': '🔍 正在检索相关医疗知识库...', 'progress': 45}, ensure_ascii=False)}\n"
        await asyncio.sleep(0.3)

        yield f"{json.dumps({'type': 'progress', 'message': '🧠 AI医生正在分析您的情况...', 'progress': 60}, ensure_ascii=False)}\n"

        # 准备工作流执行
        logger.info(f"[{request_id}] 开始执行工作流 - maternal_id: {request.maternal_id}, chat_id: {request.chat_id}")
        workflow_graph = prengant_workflow()
        workflow_state: PrengantState = {
            "input": request.input,
            "maternal_id": request.maternal_id,
            "chat_id": request.chat_id,
            "user_type": request.user_type,
            "timestamp": request.timestamp,
            "file_id": request.file_id or []
        }

        # 执行流式工作流（真正的AI流式输出）
        workflow_start_time = time.time()
        logger.info(f"[{request_id}] 开始流式工作流 - 开始时间: {workflow_start_time}")

        # 引入流式工作流
        from backend.workflow.test import prengant_workflow_stream

        # 发送AI开始生成的消息
        yield f"{json.dumps({'type': 'progress', 'message': '🤖 AI医生开始回答...', 'progress': 70}, ensure_ascii=False)}\n"

        # 实时流式输出AI生成的内容
        full_response = ""
        chunk_count = 0

        async for ai_chunk in prengant_workflow_stream(workflow_state):
            chunk_count += 1
            full_response += ai_chunk

            # 实时发送AI生成的每个chunk给前端
            yield f"{json.dumps({'type': 'ai_content', 'content': ai_chunk, 'chunk_id': chunk_count}, ensure_ascii=False)}\n"

            # 可选：每隔几个chunk发送一次进度更新
            if chunk_count % 10 == 0:
                progress = min(70 + (chunk_count // 10), 95)
                yield f"{json.dumps({'type': 'progress', 'message': f'💭 AI正在思考... ({chunk_count} tokens)', 'progress': progress}, ensure_ascii=False)}\n"

        workflow_end_time = time.time()
        workflow_duration = workflow_end_time - workflow_start_time

        logger.info(f"[{request_id}] 流式工作流完成 - 耗时: {workflow_duration:.2f}s, chunks: {chunk_count}")

        # 设置最终的AI回复内容
        workflow_output = full_response.strip() if full_response.strip() else None
        workflow_error = None if workflow_output else "AI未生成有效回复"

        yield f"{json.dumps({'type': 'progress', 'message': f'✅ AI回复完成（耗时 {workflow_duration:.1f}秒，共 {chunk_count} tokens）', 'progress': 95}, ensure_ascii=False)}\n"

        # 构造助手消息
        assistant_message: Optional[MessageItem] = None
        if workflow_output:
            assistant_message_id = f"msg_{uuid.uuid4()}"
            assistant_content: List[MessageContent] = [TextContent(type="text", text=workflow_output)]
            user_dt = datetime.strptime(request.timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
            assistant_dt = user_dt + timedelta(seconds=int(workflow_duration))
            assistant_message = MessageItem(
                message_id=assistant_message_id,
                role="assistant",
                content=assistant_content,
                timestamp=assistant_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            )

        # 构造会话标题
        session_title = request.input[:10] + "..." if len(request.input) > 10 else request.input
        if not session_title:
            session_title = "未命名会话"

        # 构造响应数据
        workflow_data = WorkflowData(
            chat_meta=ChatMeta(
                chat_id=request.chat_id,
                user_type=request.user_type,
                maternal_id=request.maternal_id
            ),
            session_title=session_title,
            messages=[user_message] + ([assistant_message] if assistant_message else []),
            error=workflow_error
        )

        answer = PregnantWorkflowResponse(
            code=200 if workflow_output else 500,
            msg="success" if workflow_output else "工作流未生成有效回答",
            data=workflow_data
        )

        # 保存结果
        if workflow_output:
            try:
                yield f"{json.dumps({'type': 'progress', 'message': '💾 正在保存对话记录...', 'progress': 95}, ensure_ascii=False)}\n"

                json_file_path = maternal_service.get_dialogue_content_by_chat_id(request.chat_id)
                if isinstance(json_file_path, str):
                    os.makedirs(os.path.dirname(json_file_path), exist_ok=True)

                    existing_data = []
                    if os.path.exists(json_file_path):
                        try:
                            with open(json_file_path, 'r', encoding='utf-8') as f:
                                existing_data = json.load(f)
                                if not isinstance(existing_data, list):
                                    existing_data = [existing_data]
                        except json.JSONDecodeError:
                            existing_data = []

                    existing_data.append(answer.model_dump())
                    with open(json_file_path, 'w', encoding='utf-8') as f:
                        json.dump(existing_data, f, ensure_ascii=False, indent=2)

                    logger.info(f"答案已保存到JSON文件: {json_file_path}")
            except Exception as e:
                logger.error(f"保存JSON文件失败: {str(e)}")
                yield f"{json.dumps({'type': 'warning', 'message': '⚠️ 对话记录保存失败，但结果已生成', 'progress': 95}, ensure_ascii=False)}\n"

        # 计算总耗时
        total_duration = time.time() - start_time

        # 发送最终结果
        yield f"{json.dumps({'type': 'complete', 'message': f'🎉 处理完成！总耗时 {total_duration:.1f}秒', 'data': answer.model_dump(), 'progress': 100, 'duration': total_duration}, ensure_ascii=False)}\n"

        # 关闭连接
        yield f"{json.dumps({'type': 'done'}, ensure_ascii=False)}\n"

    except Exception as e:
        error_msg = f"工作流执行异常：{str(e)}"
        logger.error(error_msg, exc_info=True)

        # 发送错误消息
        yield f"{json.dumps({'type': 'error', 'message': f'❌ 处理失败: {error_msg}', 'progress': 0}, ensure_ascii=False)}\n"
        yield f"{json.dumps({'type': 'done'}, ensure_ascii=False)}\n"

# ------------------------------
# 4. 工作流调用接口实现
# ------------------------------

@router.post(
    "/qa",
    summary="孕妇工作流调用接口（流式返回）",
    description="""
    调用孕妇专属智能工作流，支持实时流式返回：

    **功能特性**：
    1. 立即开始流式响应，实时推送处理进度
    2. 通过Server-Sent Events返回进度和最终结果
    3. 用户可实时看到处理状态，无需等待
    4. 连接结束后直接获得完整对话数据
    5. 支持多用户并发（20个并发 + 50个队列）

    **响应格式（Server-Sent Events）**：
    - type: start - 处理开始
    - type: progress - 处理进度更新（含进度百分比）
    - type: ai_content - AI实时生成内容
    - type: complete - 处理完成，包含完整结果
    - type: error - 处理失败
    """,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "JSON Lines 流式响应",
            "content": {
                "application/x-ndjson": {
                    "example": "{\"type\":\"start\",\"message\":\"🚀 开始处理您的问题...\"}\n{\"type\":\"ai_content\",\"content\":\"您好\",\"chunk_id\":1}\n{\"type\":\"done\"}\n"
                }
            }
        }
    }
)
async def invoke_pregnant_workflow_stream(
    request: PregnantWorkflowRequest,
    use_queue: bool = Query(False, description="是否使用请求队列（高负载时推荐开启）")
):
    """调用孕妇工作流（流式返回）"""
    try:
        # 确保队列处理器已启动
        await ensure_queue_processor_started()

        logger.info(f"开始流式工作流：maternal_id={request.maternal_id}, chat_id={request.chat_id}, use_queue={use_queue}")

        if use_queue:
            # 使用队列模式处理
            if request_queue.full():
                # 队列已满，返回错误
                logger.warning(f"请求队列已满，拒绝请求：maternal_id={request.maternal_id}")
                raise HTTPException(
                    status_code=503,
                    detail="服务器繁忙，请稍后重试"
                )

            # 将请求放入队列
            response_future = asyncio.Future()
            await request_queue.put((request.model_dump(), response_future))
            update_queue_waiting(request_queue.qsize())

            logger.info(f"请求已加入队列：maternal_id={request.maternal_id}, 队列大小={request_queue.qsize()}")

            # 等待队列处理结果并返回流式响应
            return StreamingResponse(
                wait_for_queue_result(response_future),
                media_type="application/x-ndjson",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control"
                }
            )
        else:
            # 直接处理模式
            return StreamingResponse(
                execute_workflow_stream_protected(request.model_dump()),
                media_type="application/x-ndjson",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control"
                }
            )

    except Exception as e:
        logger.error(f"工作流调用失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动流式工作流失败: {str(e)}")

# ------------------------------
# 7. 性能监控接口
# ------------------------------

# @router.get(
#     "/qa/performance",
#     summary="获取系统性能指标",
#     description="获取当前系统的性能指标，包括并发情况、响应时间、成功率等",
#     status_code=status.HTTP_200_OK
# )
# async def get_performance_metrics():
#     """获取系统性能指标"""
#     try:
#         perf_snapshot = get_performance_snapshot()

#         return {
#             "code": 200,
#             "msg": "获取性能指标成功",
#             "data": {
#                 "timestamp": datetime.now().isoformat(),
#                 "performance": perf_snapshot,
#                 "system_config": {
#                     "max_concurrent_requests": MAX_CONCURRENT_REQUESTS,
#                     "workflow_timeout": WORKFLOW_TIMEOUT,
#                     "queue_max_size": QUEUE_MAX_SIZE
#                 },
#                 "recommendations": generate_performance_recommendations(perf_snapshot)
#             }
#         }
#     except Exception as e:
#         logger.error(f"获取性能指标失败: {e}")
#         return {
#             "code": 500,
#             "msg": f"获取性能指标失败: {str(e)}",
#             "data": None
#         }

# def generate_performance_recommendations(perf_snapshot: dict) -> List[str]:
#     """根据性能指标生成优化建议"""
#     recommendations = []

#     # 检查成功率
#     success_rate = float(perf_snapshot["success_rate"].rstrip('%'))
#     if success_rate < 90:
#         recommendations.append("🚨 成功率低于90%，建议检查系统负载和错误日志")

#     # 检查并发情况
#     active_requests = perf_snapshot["active_requests"]
#     semaphore_available = perf_snapshot["semaphore_available"]
#     if semaphore_available <= 2:
#         recommendations.append("⚠️ 并发资源紧张，建议增加MAX_CONCURRENT_REQUESTS或使用队列模式")

#     # 检查队列情况
#     queue_size = perf_snapshot["queue_size"]
#     if queue_size > QUEUE_MAX_SIZE * 0.8:
#         recommendations.append("📋 请求队列接近满载，建议增加处理能力或queue大小")

#     # 检查响应时间
#     avg_response_time = float(perf_snapshot["avg_response_time"].rstrip('s'))
#     if avg_response_time > 60:
#         recommendations.append("⏰ 平均响应时间超过60秒，建议优化工作流性能")

#     # 检查超时率
#     total_requests = perf_snapshot["total_requests"]
#     timeout_requests = perf_snapshot["timeout_requests"]
#     if total_requests > 0:
#         timeout_rate = (timeout_requests / total_requests) * 100
#         if timeout_rate > 10:
#             recommendations.append("⏱️ 超时率超过10%，建议增加WORKFLOW_TIMEOUT或优化处理逻辑")

#     if not recommendations:
#         recommendations.append("✅ 系统运行状态良好")

#     return recommendations

# @router.get(
#     "/health",
#     summary="系统健康检查",
#     description="检查系统健康状态，包括服务可用性和关键指标",
#     status_code=status.HTTP_200_OK
# )
# async def health_check():
#     """系统健康检查"""
#     try:
#         # 检查基本服务状态
#         perf_snapshot = get_performance_snapshot()

#         # 判断系统健康状态
#         is_healthy = True
#         health_issues = []

#         # 检查成功率
#         success_rate = float(perf_snapshot["success_rate"].rstrip('%'))
#         if success_rate < 80:
#             is_healthy = False
#             health_issues.append("成功率过低")

#         # 检查响应时间
#         avg_response_time = float(perf_snapshot["avg_response_time"].rstrip('s'))
#         if avg_response_time > 120:
#             is_healthy = False
#             health_issues.append("响应时间过长")

#         # 检查信号量可用性
#         if perf_snapshot["semaphore_available"] <= 0:
#             is_healthy = False
#             health_issues.append("无可用并发资源")

#         # 检查队列状态
#         if perf_snapshot["queue_size"] >= QUEUE_MAX_SIZE:
#             is_healthy = False
#             health_issues.append("请求队列已满")

#         return {
#             "status": "healthy" if is_healthy else "unhealthy",
#             "timestamp": datetime.now().isoformat(),
#             "version": "v2.0.0",
#             "uptime": "unknown",  # 可以添加启动时间记录
#             "performance": perf_snapshot,
#             "issues": health_issues if health_issues else None
#         }

#     except Exception as e:
#         logger.error(f"健康检查失败: {e}")
#         return {
#             "status": "error",
#             "timestamp": datetime.now().isoformat(),
#             "error": str(e)
#         }


# ------------------------------
# 2. 核心接口实现（根据 chat_id 获取对话历史）
# ------------------------------


@router.get(
    path = '/{chat_id}/history',
    summary = '根据',
    description = '根据对话ID获取对话历史'
)
async def get_chat_history_by_ids(
    chat_id: str = Path(..., description="对话ID")
):
    json_file_path = maternal_service.get_dialogue_content_by_chat_id(chat_id)
    if not isinstance(json_file_path, str):
        raise HTTPException(status_code=404, detail="对话文件不存在")
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data

# ------------------------------
# 2. 核心接口实现（根据 chat_id 获取对话历史）
# ------------------------------
class GetChatIdsRequest(BaseModel):
    maternal_id: int = Field(..., description="孕妇ID")


@router.post(
    path = '/get_chat_ids',
    summary = '原本路由根据孕妇ID获取对话ID列表',
    description = '根据孕妇ID获取所有对话记录的对话ID列表'
)
async def get_chat_ids_by_maternal_id(
    request: GetChatIdsRequest
):
    chat_ids = maternal_service.get_chat_id_by_maternal_id(request.maternal_id)
    return chat_ids


# ------------------------------
# 6. 医疗文件相关接口
# ------------------------------
@router.post(
    path="/{user_id}/files",
    status_code=status.HTTP_201_CREATED,
    summary="上传孕妇医疗文件",
    description="上传孕妇医疗文件（支持jpg/png/pdf等，需form-data格式）"
)
# @require_auth  # 如需认证可取消注释
def upload_medical_file(
    user_id: int = Path(..., description="孕妇唯一ID（正整数）"),
    # 文件参数：FastAPI原生UploadFile，自动处理文件流
    file: UploadFile = File(..., description="上传的医疗文件（必填）"),
    # 表单参数：用Form标注（form-data中的非文件字段）
    file_desc: str | None = Form(None, description="文件描述（可选）"),
    check_date_str: str | None = Form(None, description="检查日期（格式：YYYY-MM-DD，可选）")
):
    try:
        # 1. 验证文件合法性
        if not file.filename:
            return JSONResponse(
                content={"status": "error", "message": "未选择文件或文件名为空"},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 检查文件大小
        file_content = file.file.read()
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            return JSONResponse(
                content={"status": "error", "message": "文件大小不能超过10MB"},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 2. 处理文件存储目录
        base_upload_dir = "uploads/maternal_files"
        user_dir = os.path.join(base_upload_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)  # 不存在则创建目录

        # 3. 生成唯一文件名（避免冲突）
        file_ext = os.path.splitext(file.filename)[1].lower()  # 提取文件后缀（小写）
        unique_filename = f"{uuid.uuid4()}{file_ext}"  # UUID生成唯一文件名
        file_path = os.path.join(user_dir, unique_filename)

        # 4. 保存文件到服务器（FastAPI UploadFile 需用文件对象保存）
        with open(file_path, "wb") as f:
            f.write(file_content)  # 读取上传文件的二进制内容并写入

        # 5. 处理检查日期
        check_date = None
        if check_date_str:
            check_date = datetime.strptime(check_date_str, "%Y-%m-%d").date()

        # 6. 获取文件元信息
        file_size = os.path.getsize(file_path)  # 文件大小（字节）
        file_type = file.content_type or file_ext.lstrip(".")  # 优先用MIME类型，其次后缀

        # 7. 调用业务层保存到数据库
        db_result = maternal_service.create_medical_file(
            maternal_id=user_id,
            file_name=file.filename,  # 原始文件名
            file_path=file_path,      # 服务器存储路径
            file_type=file_type,
            file_size=file_size,
            upload_time=datetime.now(),
            file_desc=file_desc,
            check_date=check_date
        )

        # 8. 构造响应（返回关键信息）
        file_id = None
        if hasattr(db_result, "id"):
            file_id = getattr(db_result, "id")
        elif isinstance(db_result, dict) and "id" in db_result:
            file_id = db_result["id"]
        
        return {
            "status": "success",
            "message": "医疗文件上传成功",
            "data": {
                "file_id": file_id,
                "original_filename": file.filename,
                "storage_path": file_path,
                "file_type": file_type,
                "file_size": file_size,
                "upload_time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "check_date": check_date.strftime("%Y-%m-%d") if check_date else None,
                "file_desc": file_desc
            }
        }

    except Exception as e:
        # 出错时清理已保存的文件（避免垃圾文件）
        file_path_local = locals().get("file_path")
        if file_path_local and os.path.exists(file_path_local):
            try:
                os.remove(file_path_local)
            except OSError:
                pass  # 忽略删除文件时的错误
        
        return JSONResponse(
            content={"status": "error", "message": f"文件上传失败：{str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    finally:
        # 关闭文件流（避免资源泄漏）
        file.file.close()

class GetMedicalFilesRequest(BaseModel):
    file_id: str = Field(..., description="孕妇ID")

@router.get(
    path="/{user_id}/files",
    status_code=status.HTTP_200_OK,
    summary="根据file_id获取孕妇医疗文件信息",
    description="根据file_id获取孕妇医疗文件信息"
)
# @require_auth  # 如需认证可取消注释
def get_medical_files(
    request: GetMedicalFilesRequest
):
    try:
        file_records = maternal_service.get_medical_file_by_fileid(request.file_id)
        
        return {
            "status": "success",
            "count": len(file_records),
            "data": file_records
        }
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": f"获取文件记录失败：{str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get(
    path="/{user_id}/files/{file_id}/download",
    status_code=status.HTTP_200_OK,
    summary="下载孕妇医疗文件",
    description="根据用户ID和文件ID下载指定的医疗文件"
)
# @require_auth  # 如需认证可取消注释
def download_medical_file(
    user_id: int = Path(..., description="孕妇唯一ID（正整数）"),
    file_id: str = Path(..., description="文件唯一ID（正整数）")
):
    """下载医疗文件"""
    try:
        # 1. 获取文件信息
        file_info = maternal_service.get_medical_file_by_fileid(file_id)
        
        if not file_info:
            return JSONResponse(
                content={"status": "error", "message": "文件不存在"},
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # 2. 验证文件归属权（确保文件属于指定的孕妇）
        if file_info["maternal_id"] != user_id:
            return JSONResponse(
                content={"status": "error", "message": "无权访问该文件"},
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # 3. 检查文件是否存在于服务器
        file_path = file_info["file_path"]
        
        # 4. 安全检查：防止路径遍历攻击
        # 确保文件路径在允许的上传目录范围内
        allowed_base_dir = os.path.abspath("uploads/maternal_files")
        actual_file_path = os.path.abspath(file_path)
        
        if not actual_file_path.startswith(allowed_base_dir):
            return JSONResponse(
                content={"status": "error", "message": "非法文件路径"},
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        if not os.path.exists(file_path):
            return JSONResponse(
                content={"status": "error", "message": "文件在服务器上不存在"},
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # 5. 确定文件的MIME类型
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = "application/octet-stream"  # 默认二进制类型
        
        # 6. 返回文件响应
        return FileResponse(
            path=file_path,
            media_type=mime_type,
            filename=file_info["file_name"],  # 使用原始文件名
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{file_info['file_name']}",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
        )
        
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        return JSONResponse(
            content={"status": "error", "message": f"下载文件失败：{str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get(
    path="/{user_id}/files/list",
    status_code=status.HTTP_200_OK,
    summary="获取用户的所有医疗文件列表",
    description="根据用户ID获取该用户上传的所有医疗文件列表"
)
# @require_auth  # 如需认证可取消注释
def list_medical_files(
    user_id: int = Path(..., description="孕妇唯一ID（正整数）"),
    file_name: Optional[str] = Query(None, description="可选的文件名过滤条件")
):
    """获取用户的医疗文件列表"""
    try:
        # 获取文件列表
        file_records = maternal_service.get_medical_files(user_id, file_name or "")
        
        # 为每个文件添加下载链接
        for record in file_records:
            # 添加下载URL（前端可以通过此URL直接下载文件）
            record["download_url"] = f"/api/v2/chat/{user_id}/files/{record['id']}/download"
            
            # 检查文件是否仍然存在于服务器上
            record["file_exists"] = os.path.exists(record["file_path"])
        
        return {
            "status": "success",
            "count": len(file_records),
            "data": file_records
        }
        
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        return JSONResponse(
            content={"status": "error", "message": f"获取文件列表失败：{str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
