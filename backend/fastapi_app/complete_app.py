"""
完整的FastAPI应用
整合API和Web界面功能
"""

import sys
import os
import time
import uuid
from pathlib import Path
from threading import Timer
from typing import Optional
from contextlib import asynccontextmanager

# 添加项目根目录到系统路径
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.chat_message_histories import ChatMessageHistory

from .config import settings
from .routers import auth, chat, maternal
from .models import error_response
from backend.agent.core import ObstetricsAgent
from backend.knowledge_base.loader import DocumentLoader

# Web相关全局变量
obstetrics_agent = None
user_sessions = {}
SESSION_TIMEOUT = 3600

def cleanup_sessions():
    """清理过期会话"""
    current_time = time.time()
    expired_ids = [
        sid for sid, (hist, timestamp) in user_sessions.items() 
        if current_time - timestamp > SESSION_TIMEOUT
    ]
    for sid in expired_ids:
        del user_sessions[sid]
    Timer(SESSION_TIMEOUT, cleanup_sessions).start()

# 应用启动和关闭事件处理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global obstetrics_agent
    
    # 启动时执行
    print("🚀 完整FastAPI应用启动")
    print(f"📝 应用名称: {settings.app_name}")
    print(f"🔧 版本: {settings.app_version}")
    print(f"🏠 监听地址: {settings.host}:{settings.port}")
    
    # 初始化Agent
    try:
        obstetrics_agent = ObstetricsAgent()
        print("🤖 产科智能体初始化成功")
    except Exception as e:
        print(f"❌ 产科智能体初始化失败: {e}")
    
    # 启动会话清理
    cleanup_sessions()
    print("🧹 会话清理任务启动")
    
    yield
    
    # 关闭时执行
    print("🛑 FastAPI应用关闭")

# 创建FastAPI应用实例
app = FastAPI(
    title=f"{settings.app_name} - 完整版",
    version=settings.app_version,
    description="集成API和Web界面的完整孕产智能问答系统",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# ==================== 中间件配置 ====================

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# ==================== 静态文件和模板 ====================

# 设置模板目录
try:
    templates = Jinja2Templates(directory="web/templates")
    print("📄 模板目录配置成功")
except Exception as e:
    print(f"❌ 模板目录配置失败: {e}")
    templates = None

# ==================== 异常处理器 ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=exc.detail,
            error_code=f"HTTP_{exc.status_code}"
        )
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    error_detail = str(exc) if settings.debug else "内部服务器错误"
    return JSONResponse(
        status_code=500,
        content=error_response(
            message="内部服务器错误",
            detail=error_detail,
            error_code="INTERNAL_ERROR"
        )
    )

# ==================== API路由注册 ====================

# 注册API路由
app.include_router(auth.router, tags=["认证"])
app.include_router(chat.router, tags=["聊天"])
app.include_router(maternal.router, tags=["孕妇信息"])

# ==================== Web界面路由 ====================

@app.get("/", response_class=HTMLResponse, tags=["Web界面"], summary="首页")
async def index(request: Request):
    """Web界面首页"""
    if not templates:
        return HTMLResponse("<h1>模板系统未配置</h1>")
    
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        return HTMLResponse(f"<h1>页面加载失败: {e}</h1>")

@app.post("/api/new_conversation", tags=["Web界面"], summary="创建新对话")
async def new_conversation():
    """创建新对话会话"""
    session_id = str(uuid.uuid4())
    user_sessions[session_id] = (ChatMessageHistory(), time.time())
    return {"status": "success", "session_id": session_id}

@app.post("/api/qa", tags=["Web界面"], summary="Web版医疗问答")
async def web_medical_qa(
    query: str = Form(..., description="查询内容"),
    user_type: str = Form(default="doctor", description="用户类型"),
    session_id: Optional[str] = Form(None, description="会话ID"),
    image: Optional[UploadFile] = File(None, description="上传的图片或文档")
):
    """Web版医疗问答接口"""
    global obstetrics_agent
    
    try:
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="查询内容不能为空")
        
        if not obstetrics_agent:
            raise HTTPException(status_code=503, detail="智能体服务未就绪")
        
        # 处理会话ID
        if not session_id:
            session_id = str(uuid.uuid4())
            user_sessions[session_id] = (ChatMessageHistory(), time.time())
        else:
            if session_id not in user_sessions:
                user_sessions[session_id] = (ChatMessageHistory(), time.time())
            else:
                user_sessions[session_id] = (user_sessions[session_id][0], time.time())

        history, _ = user_sessions[session_id]
        
        # 处理上传文件
        image_path = None
        document_content = None
        
        if image and image.filename:
            upload_dir = os.path.join(settings.upload_dir, "web")
            os.makedirs(upload_dir, exist_ok=True)
            
            # 生成唯一文件名
            file_ext = os.path.splitext(image.filename)[1].lower()
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            # 保存文件
            with open(file_path, "wb") as buffer:
                content = await image.read()
                buffer.write(content)
            
            # 处理不同类型文件
            if file_ext in ['.png', '.jpg', '.jpeg']:
                image_path = file_path
            elif file_ext in ['.pdf', '.docx', '.doc', '.txt']:
                try:
                    loader = DocumentLoader(file_path)
                    documents = loader.load()
                    document_content = "\n\n".join([doc.page_content for doc in documents])
                except Exception as e:
                    document_content = f"文档处理失败: {str(e)}"
        
        # 设置Agent记忆并处理查询
        obstetrics_agent.memory.chat_memory = history
        response = obstetrics_agent.invoke(query, user_type=user_type)
        
        # 清理临时文件
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        return {
            "answer": response,
            "session_id": session_id,
            "history_length": len(history.messages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

@app.get("/api/session/{session_id}/history", tags=["Web界面"], summary="获取Web会话历史")
async def get_web_session_history(session_id: str):
    """获取Web会话历史"""
    if session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    history, _ = user_sessions[session_id]
    messages = [
        {
            "type": "human" if msg.type == "human" else "ai",
            "content": msg.content
        }
        for msg in history.messages
    ]
    
    return {
        "status": "success",
        "session_id": session_id,
        "history": messages,
        "length": len(messages)
    }

# ==================== 系统信息路由 ====================

@app.get("/health", tags=["系统"], summary="健康检查")
async def health_check():
    """系统健康检查"""
    return {
        "status": "healthy",
        "api_status": "ready",
        "web_status": "ready" if templates else "disabled",
        "agent_status": "ready" if obstetrics_agent else "not_ready",
        "active_sessions": len(user_sessions),
        "version": settings.app_version
    }

@app.get("/info", tags=["系统"], summary="系统信息")
async def system_info():
    """系统信息"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
        "features": {
            "api": True,
            "web_ui": templates is not None,
            "file_upload": True,
            "authentication": True,
            "agent": obstetrics_agent is not None
        },
        "endpoints": {
            "web_ui": "/",
            "api_docs": "/docs" if settings.debug else "disabled",
            "health": "/health",
            "auth": "/api/v1/auth",
            "chat": "/api/v1/chat",
            "maternal": "/api/v1/maternal"
        }
    }

# ==================== 启动配置 ====================

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 启动完整FastAPI应用...")
    uvicorn.run(
        "complete_app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning",
        access_log=settings.debug
    )