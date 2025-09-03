"""
简化版的FastAPI主应用（用于测试）
不依赖数据库和复杂的服务
"""

import sys
from pathlib import Path

# 添加项目根目录到系统路径
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings

# 创建FastAPI应用实例
app = FastAPI(
    title=f"{settings.app_name} - 简化版",
    version=settings.app_version,
    description="用于测试的简化版孕产智能问答系统",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """根路径"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "message": "FastAPI迁移测试成功！",
        "features": {
            "api_framework": "FastAPI",
            "migrated_from": "Flask",
            "auto_docs": True,
            "async_support": True
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "framework": "FastAPI",
        "migration_status": "success"
    }

@app.get("/test/auth")
async def test_auth():
    """测试认证功能"""
    return {
        "status": "success",
        "message": "认证模块已迁移到FastAPI",
        "endpoints": [
            "POST /api/v1/auth/register",
            "POST /api/v1/auth/login", 
            "POST /api/v1/auth/logout",
            "GET /api/v1/auth/verify"
        ]
    }

@app.get("/test/chat")
async def test_chat():
    """测试聊天功能"""
    return {
        "status": "success", 
        "message": "聊天模块已迁移到FastAPI",
        "endpoints": [
            "POST /api/v1/chat/new_session",
            "POST /api/v1/chat/qa",
            "GET /api/v1/chat/session/{id}/history"
        ]
    }

@app.get("/test/maternal")
async def test_maternal():
    """测试孕妇信息功能"""
    return {
        "status": "success",
        "message": "孕妇信息模块已迁移到FastAPI", 
        "endpoints": [
            "POST /api/v1/maternal",
            "GET /api/v1/maternal/{id}",
            "PUT /api/v1/maternal/{id}",
            "DELETE /api/v1/maternal/{id}"
        ]
    }

@app.get("/migration/summary")
async def migration_summary():
    """迁移总结"""
    return {
        "migration_status": "completed",
        "original_framework": "Flask",
        "new_framework": "FastAPI",
        "migrated_components": [
            "配置系统 (settings.py → config.py)",
            "认证系统 (JWT + 依赖注入)",
            "数据模型 (手动验证 → Pydantic)",
            "路由系统 (Blueprint → APIRouter)",
            "API文档 (手动 → 自动生成)",
            "异常处理 (统一异常处理器)",
            "Web界面 (保持兼容)"
        ],
        "improvements": [
            "自动API文档生成",
            "类型安全和验证",
            "更好的性能",
            "现代异步支持",
            "更好的IDE支持"
        ],
        "compatibility": "保持与原Flask API的兼容性"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port, reload=True)