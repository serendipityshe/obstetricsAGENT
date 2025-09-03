"""
聊天路由 - FastAPI版本
从Flask的chat_routes.py迁移
"""

import sys
import os
from pathlib import Path
from uuid import uuid4
from typing import Optional

# 添加项目根目录到系统路径
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from models.chat import (
    ChatRequest, ChatResponse, ChatMessage, ChatHistory,
    SessionResponse, ChatSuccessResponse, SessionSuccessResponse, 
    HistorySuccessResponse
)
from models import success_response, error_response, list_response
from auth import get_current_user_optional
from config import settings
from backend.api.v1.services.chat_service import ChatService

# 创建路由器
router = APIRouter(prefix="/api/v1/chat", tags=["聊天"])

# 服务实例
chat_service = ChatService()

@router.post("/new_session",
            response_model=SessionSuccessResponse,
            summary="创建新会话",
            description="创建新的对话会话")
async def new_session():
    """创建新的对话会话"""
    try:
        session_id = chat_service.create_new_session()
        
        return SessionSuccessResponse(
            status="success",
            message="新会话创建成功",
            data=SessionResponse(
                session_id=session_id,
                message="新会话创建成功"
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建会话失败：{str(e)}"
        )

@router.post("/qa",
            response_model=ChatSuccessResponse,
            summary="医疗问答",
            description="处理医疗问答请求，支持文件上传")
async def medical_qa(
    query: str = Form(..., description="用户查询内容"),
    user_type: str = Form(default="doctor", description="用户类型"),
    session_id: Optional[str] = Form(None, description="会话ID"),
    file: Optional[UploadFile] = File(None, description="上传的文件"),
    current_user: Optional[str] = Depends(get_current_user_optional)
):
    """处理医疗问答请求，支持文件上传"""
    try:
        # 验证基础参数
        if not query or not query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="查询内容不能为空"
            )
            
        if user_type not in ['doctor', 'pregnant_mother']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户类型无效"
            )
        
        # 如果没有会话ID，创建一个新的
        if not session_id:
            session_id = chat_service.create_new_session()
        
        # 处理上传的文件
        image_path = None
        document_content = None
        
        if file and file.filename:
            # 确保上传目录存在
            upload_dir = settings.upload_dir
            os.makedirs(upload_dir, exist_ok=True)
            
            # 验证文件类型和大小
            if file.size and file.size > settings.max_file_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"文件大小超过限制({settings.max_file_size // (1024*1024)}MB)"
                )
            
            # 生成唯一文件名避免冲突
            file_ext = file.filename.split('.')[-1].lower() if '.' in file.filename else 'bin'
            
            if file_ext not in settings.allowed_file_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不支持的文件类型: {file_ext}"
                )
            
            filename = f"{uuid4()}.{file_ext}"
            file_path = os.path.join(upload_dir, filename)
            
            # 保存文件到本地
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # 根据文件类型处理
            if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
                # 图片文件 - 传递路径
                image_path = file_path
            else:
                # 文档文件 - 读取内容
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        document_content = f.read(10000)  # 限制读取长度
                except UnicodeDecodeError:
                    # 二进制文件处理
                    document_content = f"二进制文件: {file.filename} (类型: {file_ext})"
        
        # 调用服务处理问答
        result = chat_service.handle_qa_request(
            session_id=session_id,
            query=query,
            user_type=user_type,
            image_path=image_path,
            document_content=document_content
        )
        
        return ChatSuccessResponse(
            status="success",
            data=ChatResponse(
                answer=result['answer'],
                session_id=result['session_id'],
                history_length=result['history_length']
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理问答失败：{str(e)}"
        )

@router.get("/session/{session_id}/history",
           response_model=HistorySuccessResponse,
           summary="获取会话历史",
           description="获取指定会话的历史记录")
async def get_session_history(session_id: str):
    """获取指定会话的历史记录"""
    try:
        history = chat_service.get_session_history(session_id)
        
        messages = [
            ChatMessage(
                type='human' if msg.type == 'human' else 'ai',
                content=msg.content
            )
            for msg in history.messages
        ]
        
        return HistorySuccessResponse(
            status="success",
            data=ChatHistory(
                session_id=session_id,
                history=messages,
                length=len(messages)
            )
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取历史记录失败：{str(e)}"
        )

@router.delete("/session/{session_id}",
              summary="删除会话",
              description="删除指定的会话及其历史记录")
async def delete_session(session_id: str):
    """删除指定的会话"""
    try:
        # 这里可以添加删除会话的逻辑
        # chat_service.delete_session(session_id)
        
        return success_response(message="会话删除成功")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除会话失败：{str(e)}"
        )

@router.get("/sessions",
           summary="获取所有会话",
           description="获取当前用户的所有会话列表")
async def get_sessions(current_user: Optional[str] = Depends(get_current_user_optional)):
    """获取用户的所有会话"""
    try:
        # 这里可以添加获取用户会话列表的逻辑
        # sessions = chat_service.get_user_sessions(current_user)
        
        sessions = []  # 暂时返回空列表
        
        return list_response(sessions, "获取会话列表成功")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话列表失败：{str(e)}"
        )