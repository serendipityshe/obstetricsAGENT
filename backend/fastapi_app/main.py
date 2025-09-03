"""
FastAPI主应用文件
替代Flask的app.py
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

# 添加项目根目录到系统路径
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from config import settings
from routers import auth, chat, maternal
from models import error_response

# 应用启动和关闭事件处理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("🚀 FastAPI应用启动")
    print(f"📝 应用名称: {settings.app_name}")
    print(f"🔧 版本: {settings.app_version}")
    print(f"🏠 监听地址: {settings.host}:{settings.port}")
    print(f"🔒 调试模式: {settings.debug}")
    
    yield
    
    # 关闭时执行
    print("🛑 FastAPI应用关闭")

# 创建FastAPI应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于RAG和LLM的智能孕产问答系统 - FastAPI版本",
    docs_url="/docs" if settings.debug else None,  # 生产环境关闭文档
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# ==================== 中间件配置 ====================

# CORS中间件 - 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# 信任的主机中间件（生产环境安全）
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", settings.host]
    )

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
    if settings.debug:
        # 开发环境显示详细错误
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="内部服务器错误",
                detail=str(exc),
                error_code="INTERNAL_ERROR"
            )
        )
    else:
        # 生产环境隐藏错误详情
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="内部服务器错误",
                error_code="INTERNAL_ERROR"
            )
        )

# ==================== 路由注册 ====================

# 注册所有路由
app.include_router(auth.router, tags=["认证"])
app.include_router(chat.router, tags=["聊天"])
app.include_router(maternal.router, tags=["孕妇信息"])

# ==================== 根路径和健康检查 ====================

@app.get("/", summary="根路径", description="API根路径，返回基本信息")
async def root():
    """根路径"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "message": "孕产智能问答系统 FastAPI 版本正在运行",
        "docs_url": "/docs" if settings.debug else "文档已在生产环境中禁用",
        "endpoints": {
            "认证": "/api/v1/auth",
            "聊天": "/api/v1/chat", 
            "孕妇信息": "/api/v1/maternal"
        }
    }

@app.get("/health", summary="健康检查", description="检查应用健康状态")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": str(Path(__file__).stat().st_mtime),
        "version": settings.app_version
    }

@app.get("/info", summary="应用信息", description="获取应用详细信息")
async def app_info():
    """应用信息"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
        "environment": "development" if settings.debug else "production",
        "cors_enabled": bool(settings.cors_origins),
        "auth_enabled": True,
        "file_upload_enabled": True,
        "max_file_size_mb": settings.max_file_size // (1024 * 1024),
        "allowed_file_types": settings.allowed_file_types
    }

# ==================== 自定义OpenAPI ====================

def custom_openapi():
    """自定义OpenAPI模式"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.app_version,
        description="基于RAG和LLM的智能孕产问答系统API文档",
        routes=app.routes,
    )
    
    # 添加安全定义
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "输入JWT令牌，格式: Bearer <token>"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# 设置自定义OpenAPI
app.openapi = custom_openapi

# ==================== 启动配置 ====================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning",
        access_log=settings.debug
    )