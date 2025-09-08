from fastapi import APIRouter, HTTPException, status, Depends, Form, Path 
from pydantic import BaseModel, Field
from typing import Optional, List
import datetime

from backend.workflow.test import prengant_workflow
from backend.api.v1.services.maternal_service import MaternalService  # 复用服务层
import logging

# 初始化日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("pregnant-workflow-api")

# 初始化路由（标签与现有聊天管理服务分类一致）
router = APIRouter(tags=["聊天管理服务"])

# ------------------------------
# 1. 定义请求/响应模型（Pydantic验证）
# ------------------------------
class PregnantWorkflowRequest(BaseModel):
    """孕妇工作流调用请求模型（对应PrengantState必填/可选字段）"""
    input: str = Field(..., description="用户输入的问题/需求（如：孕妇最近出现头晕症状，需要什么建议？）")
    maternal_id: int = Field(..., description="孕妇唯一标识ID（必填，用于关联个人数据）")
    chat_id: str = Field(..., description="聊天会话ID（必填，用于追踪会话上下文）")
    user_type: str = Field(..., description="用户类型（必填，固定值：孕妇/医生/家属）")
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        description="请求时间戳（格式：YYYY-MM-DD HH:MM:SS UTC，默认自动生成）"
    )
    file_id: Optional[List[int]] = Field(None, description="关联的医疗文件ID列表（可选，如超声报告、检查单据等）")

class PregnantWorkflowResponse(BaseModel):
    """孕妇工作流调用响应模型"""
    code: int = Field(..., description="状态码（200=核心结果生成，500=无结果且报错）")
    message: str = Field(..., description="状态描述")
    data: Optional[dict] = Field(None, description="业务数据（有结果就返回，含中间错误）")
    error: Optional[str] = Field(None, description="错误信息（有错误就返回，无错误则为None）")

# ------------------------------
# 2. 工作流调用接口实现
# ------------------------------
@router.post(
    "/qa",
    summary="孕妇工作流调用接口",
    description="""
    调用孕妇专属智能工作流，处理用户需求：
    1. 支持文件关联（如医疗报告解析）
    2. 自动检索个人知识库（孕妇历史数据）与专家知识库
    3. 生成个性化建议/回答
    流程逻辑：mix节点（文件处理）→retr节点（知识检索）→proc_context（上下文拼接）→gen_synth（结果生成）
    注：无论中间节点是否报错，只要生成答案就返回结果，错误信息在error字段中
    """,
    response_model=PregnantWorkflowResponse,
    status_code=status.HTTP_200_OK
)
async def invoke_pregnant_workflow(request: PregnantWorkflowRequest):
    try:
        # 1. 基础参数预处理（转换为工作流所需的State格式）
        workflow_input = request
        logger.info(f"接收孕妇工作流请求：maternal_id={request.maternal_id}, chat_id={request.chat_id}, input={request.input[:30]}...")

        # 2. 初始化并执行工作流（即使工作流内部有非致命错误，也会返回含output的结果）
        workflow_graph = prengant_workflow()  # 获取工作流实例
        workflow_result = workflow_graph.invoke(workflow_input)  # 执行工作流
        logger.info(f"工作流执行完成：是否生成output={bool(workflow_result.get('output'))}，是否有错误={bool(workflow_result.get('error'))}")

        # 3. 提取核心数据（兼容字段缺失，用get避免KeyError）
        output = workflow_result.get("output")  # 模型生成的核心答案
        context = workflow_result.get("context", "")  # 上下文（默认空字符串）
        image_path = workflow_result.get("image_path")  # 图片文件路径
        doc_path = workflow_result.get("doc_path")  # 文档文件路径
        file_content = workflow_result.get("file_content", "")  # 文件内容（默认空字符串）
        workflow_error = workflow_result.get("error")  # 工作流内部错误（如检索失败、文件查询失败）

        # 4. 构造响应数据（无论是否有错误，只要有output就填充data）
        response_data = None
        if output:  # 核心：只要生成了答案，就构造data
            response_data = {
                "chat_id": request.chat_id,
                "maternal_id": request.maternal_id,
                "output": output,  # 必带：模型生成的答案
                "context_summary": context[:100] + "..." if len(context) > 100 else context,  # 上下文摘要（截断长文本）
                "file_info": {
                    "image_path": image_path,
                    "doc_path": doc_path,
                    "file_content": file_content[:50] + "..." if len(file_content) > 50 else file_content
                } if request.file_id else None,  # 有file_id才返回文件信息
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 响应时间戳
            }

        # 5. 确定状态码和提示信息
        if output:
            # 有核心答案：即使有错误，也返回200（前端正常展示答案）
            code = status.HTTP_200_OK
            message = "工作流核心结果生成完成（含非致命错误）" if workflow_error else "工作流处理成功"
        else:
            # 无核心答案：说明合成节点失败，返回500
            code = status.HTTP_500_INTERNAL_SERVER_ERROR
            message = "工作流处理失败（未生成答案）"
            workflow_error = workflow_error or "工作流未生成任何答案"  # 补充默认错误信息

        # 6. 返回最终响应（始终携带data和error字段，无数据则为None）
        return PregnantWorkflowResponse(
            code=code,
            message=message,
            data=response_data,
            error=workflow_error  # 保留错误信息（便于排查，不影响前端展示答案）
        )

    except Exception as e:
        # 捕获接口层未预期错误（如工作流实例化失败、参数异常）
        interface_error = f"接口执行异常：{str(e)}"
        logger.error(f"{interface_error}", exc_info=True)  # 打印详细堆栈信息
        # 即使接口层报错，也尝试返回结构化响应（避免前端接收非预期格式）
        return PregnantWorkflowResponse(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="接口调用失败（未执行工作流）",
            data=None,
            error=interface_error
        )
    