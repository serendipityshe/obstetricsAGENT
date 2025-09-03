"""
Web界面集成的FastAPI应用
将web/app.py的功能集成到FastAPI中
"""

import sys
import os
import time
import uuid
from pathlib import Path
from threading import Timer
from typing import Optional

# 添加项目根目录到系统路径
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.chat_message_histories import ChatMessageHistory

from backend.agent.core import ObstetricsAgent
from backend.knowledge_base.loader import DocumentLoader

# 创建FastAPI应用
app = FastAPI(
    title="孕产智能问答系统 - Web版",
    description="集成Web界面的FastAPI应用",
    version="2.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件和模板配置
templates = Jinja2Templates(directory="web/templates")

# 应用状态
obstetrics_agent = ObstetricsAgent()
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

# 启动时启动会话清理
cleanup_sessions()

@app.get("/", response_class=HTMLResponse, summary="首页", description="Web界面首页")
async def index(request: Request):
    """首页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/new_conversation", summary="创建新对话", description="创建新的对话会话")
async def new_conversation():
    """创建新对话"""
    session_id = str(uuid.uuid4())
    user_sessions[session_id] = (ChatMessageHistory(), time.time())
    return {"status": "success", "session_id": session_id}

@app.post("/api/qa", summary="医疗问答", description="处理医疗问答请求，支持文件上传")
async def medical_qa(
    request: Request,
    query: str = Form(..., description="查询内容"),
    user_type: str = Form(default="doctor", description="用户类型"),
    session_id: Optional[str] = Form(None, description="会话ID"),
    image: Optional[UploadFile] = File(None, description="上传的图片或文档")
):
    """医疗问答接口"""
    try:
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="查询内容不能为空")
        
        # 处理会话ID
        if not session_id:
            session_id = str(uuid.uuid4())
            user_sessions[session_id] = (ChatMessageHistory(), time.time())
        else:
            if session_id not in user_sessions:
                user_sessions[session_id] = (ChatMessageHistory(), time.time())
            else:
                # 更新会话时间戳
                user_sessions[session_id] = (user_sessions[session_id][0], time.time())

        history, _ = user_sessions[session_id]
        
        # 处理上传文件
        image_path = None
        document_content = None
        
        if image and image.filename:
            # 创建临时目录
            upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            
            # 保存文件
            file_path = os.path.join(upload_dir, image.filename)
            
            with open(file_path, "wb") as buffer:
                content = await image.read()
                buffer.write(content)
            
            # 判断文件类型
            file_ext = os.path.splitext(image.filename)[1].lower()
            if file_ext in ['.png', '.jpg', '.jpeg']:
                image_path = file_path
            elif file_ext in ['.pdf', '.docx', '.doc', '.txt']:
                try:
                    loader = DocumentLoader(file_path)
                    documents = loader.load()
                    document_content = "\n\n".join([doc.page_content for doc in documents])
                except Exception as e:
                    print(f"文档加载失败: {e}")
                    document_content = f"文档处理失败: {str(e)}"
        
        # 设置Agent的记忆
        obstetrics_agent.memory.chat_memory = history
        
        # 调用Agent处理查询
        response = obstetrics_agent.invoke(query, user_type=user_type)
        
        # 清理临时文件
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except:
                pass
        if 'file_path' in locals() and os.path.exists(file_path) and file_ext in ['.pdf', '.docx', '.doc', '.txt']:
            try:
                os.remove(file_path)
            except:
                pass
        
        return {
            "answer": response,
            "session_id": session_id,
            "history_length": len(history.messages)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/{session_id}/history", summary="获取会话历史", description="获取指定会话的历史记录")
async def get_session_history(session_id: str):
    """获取会话历史"""
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

@app.get("/api/sessions", summary="获取所有会话", description="获取所有活跃会话列表")
async def get_sessions():
    """获取所有会话"""
    sessions = []
    for session_id, (history, timestamp) in user_sessions.items():
        sessions.append({
            "session_id": session_id,
            "message_count": len(history.messages),
            "last_activity": timestamp
        })
    
    return {
        "status": "success",
        "sessions": sessions,
        "count": len(sessions)
    }

@app.delete("/api/session/{session_id}", summary="删除会话", description="删除指定的会话")
async def delete_session(session_id: str):
    """删除会话"""
    if session_id in user_sessions:
        del user_sessions[session_id]
        return {"status": "success", "message": "会话删除成功"}
    else:
        raise HTTPException(status_code=404, detail="会话不存在")

@app.get("/health", summary="健康检查", description="检查应用健康状态")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "active_sessions": len(user_sessions),
        "agent_status": "ready" if obstetrics_agent else "not_ready"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8801, reload=True)