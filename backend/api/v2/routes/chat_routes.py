from fastapi import APIRouter, HTTPException, status, Depends, Form, Path 
from pydantic import BaseModel, Field
from typing import Optional, List, Union
import datetime

import json
import uuid
import os
from backend.workflow.test import prengant_workflow
from backend.api.v1.services.maternal_service import MaternalService  # 复用服务层
import logging

# 初始化日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("pregnant-workflow-api")

# 初始化路由（标签与现有聊天管理服务分类一致）
router = APIRouter(tags=["聊天管理服务"])
maternal_service = MaternalService()

# ------------------------------
# 1. 通用工具函数（辅助生成URL、文件信息等）
# ------------------------------
def generate_temp_token() -> str:
    """生成临时URL令牌（实际项目需对接文件服务生成有效令牌）"""
    return str(uuid.uuid4())[:8]  # 取UUID前8位作为临时令牌

def get_file_size(file_path: str) -> int:
    """获取文件大小（字节），路径不存在时返回0"""
    try:
        return os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0
    except Exception as e:
        logger.warning(f"获取文件大小失败: {e}")
        return 0

def generate_expire_time(days: int = 7) -> str:
    """生成文件过期时间（当前时间+N天），格式：YYYY-MM-DD HH:MM:SS"""
    expire_dt = datetime.datetime.now() + datetime.timedelta(days=days)
    return expire_dt.strftime("%Y-%m-%d %H:%M:%S")

def get_file_name_from_path(file_path: str) -> str:
    """从文件路径中提取文件名（如无路径则返回默认名）"""
    if not file_path:
        return "unknown_file"
    return os.path.basename(file_path) or "unknown_file"

def get_file_type_from_path(file_path: str) -> str:
    """从文件路径推断MIME类型（简化版，实际项目需用专业库如python-magic）"""
    if not file_path:
        return "application/octet-stream"
    ext = os.path.splitext(file_path)[-1].lower()
    if ext in [".jpg", ".jpeg", ".png", ".gif"]:
        return f"image/{ext[1:]}"
    elif ext == ".pdf":
        return "application/pdf"
    elif ext in [".doc", ".docx"]:
        return "application/msword" if ext == ".doc" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        return "application/octet-stream"

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
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump({}, f)  # 写入空 JSON 对象，保证文件格式正确
            print(f"空 JSON 文件已创建: {json_file_path}")
            maternal_service.create_chat_record(
                maternal_id=request.maternal_id,
                chat_id=chat_id,
                json_file_path=json_file_path,
            )
        except Exception as e:
            print(f"创建空 JSON 文件失败: {str(e)}")
        return CreateChatIdRequest(
            code=200,
            msg="对话ID创建成功",
            data={"chat_id": chat_id}
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
    type: str = Field("text", Literal=True, description="内容类型：固定为text")
    text: str = Field(..., description="文本内容")

class ImageUrlInfo(BaseModel):
    """图片URL信息"""
    url: str = Field(..., description="图片文件访问URL（含令牌）")
    preview_url: str = Field(..., description="图片预览URL（缩略图）")
    file_name: str = Field(..., description="图片文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    expire_time: str = Field(..., description="URL过期时间（格式：YYYY-MM-DD HH:MM:SS）")

class ImageUrlContent(BaseModel):
    """图片类型消息内容"""
    type: str = Field("image_url", Literal=True, description="内容类型：固定为image_url")
    image_url: ImageUrlInfo = Field(..., description="图片详细信息")

class DocumentInfo(BaseModel):
    """文档URL信息"""
    url: str = Field(..., description="文档文件访问URL（含令牌）")
    file_name: str = Field(..., description="文档文件名")
    file_type: str = Field(..., description="文档MIME类型（如application/pdf）")
    file_size: int = Field(..., description="文件大小（字节）")
    expire_time: str = Field(..., description="URL过期时间（格式：YYYY-MM-DD HH:MM:SS）")

class DocumentContent(BaseModel):
    """文档类型消息内容"""
    type: str = Field("document", Literal=True, description="内容类型：固定为document")
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
        default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        description="请求时间戳（格式：YYYY-MM-DD HH:MM:SS，默认自动生成）"
    )
    file_id: Optional[List[str]] = Field(None, description="关联文件ID列表（支持图片/文档）")

# 3.6 接口最终响应模型（完全匹配目标格式）
class PregnantWorkflowResponse(BaseModel):
    """孕妇工作流调用最终响应模型"""
    code: int = Field(..., description="状态码：200=成功，500=失败")
    msg: str = Field(..., description="状态描述：success/失败原因")
    data: WorkflowData = Field(..., description="业务数据（含对话内容）")

# ------------------------------
# 4. 工作流调用接口实现
# ------------------------------
@router.post(
    "/qa",
    summary="孕妇工作流调用接口",
    description="""
    调用孕妇专属智能工作流，处理用户需求并返回结构化对话数据：
    1. 支持文本+多文件（图片/文档）混合输入
    2. 自动关联孕妇个人数据与专家知识库
    3. 返回用户-助手完整对话链（含文件URL信息）
    4. 错误信息会在data.error字段保留，不影响正常响应格式
    """,
    response_model=PregnantWorkflowResponse,
    status_code=status.HTTP_200_OK
)
async def invoke_pregnant_workflow(request: PregnantWorkflowRequest):
    try:
        # 1. 基础参数日志打印
        logger.info(
            f"接收孕妇工作流请求：maternal_id={request.maternal_id}, "
            f"chat_id={request.chat_id}, input={request.input[:30]}..."
        )

        # 2. 执行工作流（保留原逻辑）
        workflow_graph = prengant_workflow()
        workflow_result = workflow_graph.invoke(request)
        workflow_output = workflow_result.get("output")  # 助手回答
        workflow_error = workflow_result.get("error")    # 工作流内部错误
        image_path = workflow_result.get("image_path")   # 图片文件路径（工作流返回）
        doc_path = workflow_result.get("doc_path")       # 文档文件路径（工作流返回）
        logger.info(
            f"工作流执行完成：output_exists={bool(workflow_output)}, "
            f"has_error={bool(workflow_error)}, "
            f"has_image={bool(image_path)}, has_doc={bool(doc_path)}"
        )

        # 3. 构造用户消息（user角色）
        user_message_id = f"msg_{uuid.uuid4()}"  # 生成消息ID
        user_content: List[MessageContent] = []

        # 3.1 添加用户文本内容
        user_content.append(TextContent(text=request.input))

        # 3.2 添加用户文件内容（图片/文档）
        # 处理图片文件（从workflow_result的image_path提取）
        if image_path:
            file_name = get_file_name_from_path(image_path)
            file_size = get_file_size(image_path)
            token = generate_temp_token()
            # 构造图片URL（实际项目需替换为文件服务域名）
            image_url = f"https://obstetrics-mini.xxx.com/files/{request.chat_id}/{file_name}?token={token}"
            preview_url = f"https://obstetrics-mini.xxx.com/previews/{request.chat_id}/{file_name.replace(os.path.splitext(file_name)[1], '-thumb.jpg')}"
            user_content.append(ImageUrlContent(
                image_url=ImageUrlInfo(
                    url=image_url,
                    preview_url=preview_url,
                    file_name=file_name,
                    file_size=file_size,
                    expire_time=generate_expire_time()
                )
            ))

        # 处理文档文件（从workflow_result的doc_path提取）
        if doc_path:
            file_name = get_file_name_from_path(doc_path)
            file_size = get_file_size(doc_path)
            file_type = get_file_type_from_path(doc_path)
            token = generate_temp_token()
            # 构造文档URL（实际项目需替换为文件服务域名）
            doc_url = f"https://obstetrics-mini.xxx.com/files/{request.chat_id}/{file_name}?token={token}"
            user_content.append(DocumentContent(
                document=DocumentInfo(
                    url=doc_url,
                    file_name=file_name,
                    file_type=file_type,
                    file_size=file_size,
                    expire_time=generate_expire_time()
                )
            ))

        # 3.3 封装用户消息
        user_message = MessageItem(
            message_id=user_message_id,
            role="user",
            content=user_content,
            timestamp=request.timestamp
        )

        # 4. 构造助手消息（assistant角色）
        assistant_message: Optional[MessageItem] = None
        if workflow_output:
            assistant_message_id = f"msg_{uuid.uuid4()}"
            # 助手仅返回文本（可根据需求扩展多类型）
            assistant_content = [TextContent(text=workflow_output)]
            # 生成助手消息时间（比用户消息晚40秒，模拟真实响应耗时）
            user_dt = datetime.datetime.strptime(request.timestamp, "%Y-%m-%d %H:%M:%S")
            assistant_dt = user_dt + datetime.timedelta(seconds=40)
            assistant_message = MessageItem(
                message_id=assistant_message_id,
                role="assistant",
                content=assistant_content,
                timestamp=assistant_dt.strftime("%Y-%m-%d %H:%M:%S")
            )

        # 5. 构造会话标题（取用户输入前10字，超出截断）
        session_title = request.input[:10] + "..." if len(request.input) > 10 else request.input
        if not session_title:
            session_title = "未命名会话"

        # 6. 构造响应业务数据（data字段）
        workflow_data = WorkflowData(
            chat_meta=ChatMeta(
                chat_id=request.chat_id,
                user_type=request.user_type,
                maternal_id=request.maternal_id
            ),
            session_title=session_title,
            messages=[user_message] + ([assistant_message] if assistant_message else []),
            error=workflow_error  # 保留工作流错误（无错误则为None）
        )

        # 7. 构造最终响应
        if workflow_output:
            return PregnantWorkflowResponse(
                code=200,
                msg="success",
                data=workflow_data
            )
        else:
            # 无助手回答时仍返回200格式，error字段说明问题
            return PregnantWorkflowResponse(
                code=500,
                msg="工作流未生成有效回答",
                data=WorkflowData(
                    chat_meta=ChatMeta(
                        chat_id=request.chat_id,
                        user_type=request.user_type,
                        maternal_id=request.maternal_id
                    ),
                    session_title=session_title,
                    messages=[user_message],  # 仅返回用户消息
                    error=workflow_error or "工作流核心生成节点失败，未返回回答"
                )
            )

    except Exception as e:
        # 捕获接口层异常（如工作流调用失败、参数错误）
        interface_error = f"接口执行异常：{str(e)}"
        logger.error(interface_error, exc_info=True)
        # 构造异常响应（仍保持目标格式）
        user_message = MessageItem(
            message_id=f"msg_{uuid.uuid4()}",
            role="user",
            content=[TextContent(text=request.input)],
            timestamp=request.timestamp
        )
        return PregnantWorkflowResponse(
            code=500,
            msg="接口调用失败",
            data=WorkflowData(
                chat_meta=ChatMeta(
                    chat_id=request.chat_id,
                    user_type=request.user_type,
                    maternal_id=request.maternal_id
                ),
                session_title=request.input[:30] + "..." if request.input else "未命名会话",
                messages=[user_message],
                error=interface_error
            )
        )

# ------------------------------
# 5. 定义请求/响应模型（Pydantic验证）
# ------------------------------
class ChatHistoryItem(BaseModel):
    """
    单条对话记录模型
    """
    role: str = Field(..., description="角色：human(用户)/ai(智能体)")
    content: str = Field(..., description="对话内容")
    timestamp: str = Field(..., description="对话时间（格式：YYYY-MM-DD HH:MM:SS）")

class ChatHistoryData(BaseModel):
    """
    对话历史响应的业务数据模型
    """
    maternal_id: int = Field(..., description="孕妇ID")
    chat_id: int = Field(..., description="对话ID")
    history: List[ChatHistoryItem] = Field(..., description="对话历史记录")
    history_length: int = Field(..., description="对话总轮次")
    latest_update_time: str = Field(..., description="最新对话时间（格式：YYYY-MM-DD HH:MM:SS）")

class ChatHistoryResponse(BaseModel):
    """
    统一响应模型
    """
    code: int = Field(..., description="状态码：200=成功，400=记录不存在，500=系统错误")
    message: str = Field(..., description="提示信息")
    data: Optional[ChatHistoryData] = Field(None, description="业务数据")
    error: Optional[str] = Field(None, description="错误信息")

# ------------------------------
# 2. 核心接口实现（根据 maternal_id 和 chat_id 获取对话历史）
# ------------------------------
# # .get(
#     path = '{maternal_id}/{chat_id}/history',
#     summary = '根据',
#     description = '根据孕妇ID和对话ID获取对话历史'
# )
# async def get_chat_history_by_ids(
#     maternal_id: int,
#     chat_id: int
# ):
#     return ChatHistoryResponse(
#         code=200,
#         message="对话历史获取成功",
#         data=ChatHistoryData(
#             maternal_id=maternal_id,
#             chat_id=chat_id,
#             history=[],
#             history_length=0,
#             latest_update_time="2023-01-01 00:00:00"
#         )
#     )