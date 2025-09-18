#!/usr/bin/env python3
"""
测试文件下载功能的简单 FastAPI 应用
"""

import sys
from pathlib import Path

# 添加项目根目录到系统路径
root_dir = Path(__file__).parent
sys.path.append(str(root_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入我们的路由
from backend.api.v2.routes.maternal_routes import router as maternal_router
from backend.api.v2.routes.chat_routes import router as chat_router

# 创建FastAPI应用
app = FastAPI(
    title="文件下载测试应用",
    description="测试文件下载功能",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(maternal_router, prefix="/api/v2/maternal", tags=["孕妇管理"])
app.include_router(chat_router, prefix="/api/v2/chat", tags=["聊天管理"])

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "文件下载测试API服务器正在运行",
        "endpoints": {
            "文档": "/docs",
            "孕妇文件下载": "/api/v2/maternal/{maternal_id}/files/{file_id}/download",
            "聊天文件下载": "/api/v2/chat/{user_id}/files/{file_id}/download",
            "文件列表": "/api/v2/chat/{user_id}/files/list"
        }
    }

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "test_download_api:app",
        host="0.0.0.0",
        port=8801,
        reload=True,
        log_level="info"
    )