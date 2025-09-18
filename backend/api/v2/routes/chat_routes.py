from starlette.responses import JSONResponse
from fastapi import APIRouter, HTTPException, status, Depends, Form, Path, Query, UploadFile, File, Body
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse, FileResponse
from typing import Any, Optional, List, Union, Literal
from datetime import date, datetime, timedelta

import json
import uuid
import os
import mimetypes
from backend.workflow.test import prengant_workflow, PrengantState
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

        # 2. 执行工作流（保留原逻辑，将request转换为工作流状态）
        workflow_graph = prengant_workflow()
        # 将请求对象转换为工作流状态
        workflow_state: PrengantState = {
            "input": request.input,
            "maternal_id": request.maternal_id,
            "chat_id": request.chat_id,
            "user_type": request.user_type,
            "timestamp": request.timestamp,
            "file_id": request.file_id or []
        }
        workflow_result = workflow_graph.invoke(workflow_state)
        workflow_output = workflow_result.get("output")  # 助手回答
        workflow_error = workflow_result.get("error")    # 工作流内部错误
        logger.info(
            f"工作流执行完成：output_exists={bool(workflow_output)}, "
            f"has_error={bool(workflow_error)}, "
            f"file_count={len(request.file_id) if request.file_id else 0}"
        )

        # 3. 构造用户消息（user角色）
        user_message_id = f"msg_{uuid.uuid4()}"  # 生成消息ID
        user_content: List[MessageContent] = []

        # 3.1 添加用户文本内容
        user_content.append(TextContent(type="text", text=request.input))

        # 3.2 添加用户文件内容（图片/文档）
        # 处理请求中的file_id列表，根据文件类型分类到image_url或document
        if request.file_id:
            for file_id_str in request.file_id:
                try:
                    # 通过maternal_service获取文件信息
                    file_info = maternal_service.get_medical_file_by_fileid(file_id_str)
                    if file_info:
                        file_type = file_info.get("file_type", "").lower()
                        print("/n 文件类型为：", file_type)
                        
                        # 判断文件类型：图片类型
                        if (file_type.startswith("image/") or 
                            file_type in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]):
                            user_content.append(ImageUrlContent(
                                type="image_url",
                                image_url=ImageUrlInfo(
                                    file_id=file_id_str
                                )
                            ))
                        # 判断文件类型：文档类型
                        elif (file_type.startswith("application/") or 
                              file_type in ["pdf", "doc", "docx", "txt", "rtf"]):
                            user_content.append(DocumentContent(
                                type="document",
                                document=DocumentInfo(
                                    file_id=file_id_str
                                )
                            ))
                        else:
                            # 未知文件类型默认作为文档处理
                            logger.warning(f"未知文件类型 {file_type}，将作为文档处理")
                            user_content.append(DocumentContent(
                                type="document",
                                document=DocumentInfo(
                                    file_id=file_id_str
                                )
                            ))
                except Exception as e:
                    logger.error(f"处理文件ID {file_id_str} 时出错: {str(e)}")
                    continue

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
            assistant_content: List[MessageContent] = [TextContent(type="text", text=workflow_output)]
            # 生成助手消息时间（比用户消息晚40秒，模拟真实响应耗时）
            user_dt = datetime.strptime(request.timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
            assistant_dt = user_dt + timedelta(seconds=40)
            assistant_message = MessageItem(
                message_id=assistant_message_id,
                role="assistant",
                content=assistant_content,
                timestamp=assistant_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
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
        answer = PregnantWorkflowResponse(
            code=200 if workflow_output else 500,
            msg="success" if workflow_output else "工作流未生成有效回答",
            data=workflow_data
        )
        
        if workflow_output:
            try:
                # 修正变量名拼写错误
                json_file_path = maternal_service.get_dialogue_content_by_chat_id(request.chat_id)
                if not isinstance(json_file_path, str):
                    raise ValueError("获取JSON文件路径失败")
                logger.info(f"准备写入JSON文件，路径为: {json_file_path}") 
                # 确保目录存在
                os.makedirs(os.path.dirname(json_file_path), exist_ok=True)
                
                existing_data = []
                # 读取已存在数据
                if os.path.exists(json_file_path):
                    try:
                        with open(json_file_path, 'r', encoding='utf-8') as f:
                            existing_data = json.load(f)
                            if not isinstance(existing_data, list):
                                existing_data = [existing_data]
                    except json.JSONDecodeError:
                            logger.warning(f"JSON文件格式错误，将创建新文件: {json_file_path}")
                            existing_data = []
                
                # 合并数据
                existing_data.append(answer.model_dump())

                # 写入JSON文件并添加异常处理
                with open(json_file_path, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"答案已成功写入JSON文件: {json_file_path}")
            except Exception as e:
                logger.error(f"写入JSON文件失败: {str(e)}", exc_info=True)
                # 即使文件写入失败，仍返回正常响应（根据业务需求决定是否抛出异常）
                
        return answer

    except Exception as e:
        # 捕获接口层异常（如工作流调用失败、参数错误）
        interface_error = f"接口执行异常：{str(e)}"
        logger.error(interface_error, exc_info=True)
        # 构造异常响应（仍保持目标格式）
        user_message = MessageItem(
            message_id=f"msg_{uuid.uuid4()}",
            role="user",
            content=[TextContent(type="text", text=request.input)],
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
    summary="注意：！！！原接口/api/v2/maternal/{user_id}/files，已弃用，请使用新接口/api/v2/chat/{user_id}/files 上传孕妇医疗文件",
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
