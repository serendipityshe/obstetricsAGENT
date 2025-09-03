"""
FastAPI版本的配置文件
兼容原有Flask配置
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基础配置
    app_name: str = "孕产智能问答系统"
    app_version: str = "2.0.0"
    debug: bool = True
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8801
    
    # 安全配置
    secret_key: str = os.getenv("SECRET_KEY", "ad09ba2a7ede8fedb9fcf5a6b482c5e4")
    jwt_secret: str = os.getenv("JWT_SECRET", "ad09ba2a7ede8fedb9fcf5a6b482c5e4")
    jwt_expiration_hours: int = 24
    jwt_algorithm: str = "HS256"
    
    # 数据库配置
    postgres_host: str = os.getenv('POSTGRES_HOST', 'localhost')
    postgres_port: int = int(os.getenv('POSTGRES_PORT', 8802))
    postgres_user: str = os.getenv('POSTGRES_USER', 'maternal_user')
    postgres_password: str = os.getenv('POSTGRES_PASSWORD', '021030')
    postgres_database: str = os.getenv('POSTGRES_DATABASE', 'maternal_db')
    
    @property
    def database_url(self) -> str:
        """获取数据库连接URL"""
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
    
    # CORS配置
    cors_origins: list = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list = ["*"]
    cors_allow_headers: list = ["*"]
    
    # 文件上传配置
    upload_dir: str = "./uploads"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_file_types: list = ["jpg", "jpeg", "png", "gif", "bmp", "pdf", "doc", "docx", "txt"]
    
    # 会话配置
    session_timeout: int = 3600  # 1小时
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# 全局设置实例
settings = Settings()