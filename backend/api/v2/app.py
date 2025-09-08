import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from backend.api.v2.routes.auth_routes import router as auth_router
from backend.api.v2.routes.maternal_routes import router as maternal_router
from backend.api.v2.routes.chat_routes import router as chat_router


app = FastAPI(
    title="产科智能助手",
    description="基于FastAPI的母婴接口服务集合（认证/聊天/母婴数据）",
    version='1.0'
)

#不需要了
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins = ["*"],
#     allow_credentials = False,
#     allow_headers = ["*"],
#     allow_methods = ["*"]
# )

app.include_router(auth_router, prefix= "/api/v2/auth", tags= ["认证管理服务"])
app.include_router(maternal_router, prefix= "/api/v2/maternal", tags= ["孕妇数据库管理服务"])
app.include_router(chat_router, prefix= "/api/v2/chat", tags= ["聊天管理服务"])

if __name__ == '__main__':
    uvicorn.run(
        app= 'app:app',
        host= '0.0.0.0',
        port= 5000,
        reload= False,
        log_level="debug",
        reload_excludes=["*.log", "*.tmp"]
    )

