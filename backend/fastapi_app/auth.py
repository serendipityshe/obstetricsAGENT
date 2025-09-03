"""
FastAPI认证系统
JWT令牌生成和验证
"""

import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext

from config import settings

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTPBearer用于从请求头获取token
security = HTTPBearer()

# 模拟的用户凭据（实际应该从数据库获取）
USER_CREDENTIALS = {
    'doctor1': hashlib.sha256('password123'.encode()).hexdigest(),
    'admin': hashlib.sha256('adminpass'.encode()).hexdigest()
}

class AuthenticationError(HTTPException):
    """认证错误异常"""
    def __init__(self, detail: str = "认证失败"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

class TokenManager:
    """JWT令牌管理器"""
    
    @staticmethod
    def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """生成访问令牌"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
        
        to_encode = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4())  # 唯一标识符
        }
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.jwt_secret, 
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[str]:
        """验证令牌并返回用户ID"""
        try:
            payload = jwt.decode(
                token, 
                settings.jwt_secret, 
                algorithms=[settings.jwt_algorithm]
            )
            user_id: str = payload.get("user_id")
            if user_id is None:
                return None
            return user_id
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None

class PasswordManager:
    """密码管理器"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        # 兼容原有的SHA256密码格式
        if len(hashed_password) == 64:  # SHA256哈希长度
            return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password
        # 新的bcrypt格式
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """生成密码哈希"""
        return pwd_context.hash(password)

# 认证依赖函数
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    FastAPI依赖函数：从请求头获取并验证JWT令牌
    返回当前用户ID
    """
    token = credentials.credentials
    user_id = TokenManager.verify_token(token)
    
    if user_id is None:
        raise AuthenticationError("令牌无效或已过期")
    
    return user_id

# 可选的认证依赖（允许未认证访问）
async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[str]:
    """
    可选的认证依赖函数：允许未认证的请求通过
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    return TokenManager.verify_token(token)

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    验证用户凭据
    实际应用中应该从数据库查询用户信息
    """
    # 这里应该从maternal_service获取用户信息
    # 暂时使用硬编码的用户验证
    if username in USER_CREDENTIALS:
        if PasswordManager.verify_password(password, USER_CREDENTIALS[username]):
            return {
                "user_id": username,
                "username": username,
                "user_type": "doctor"  # 默认类型
            }
    return None

# 导出主要组件
__all__ = [
    "TokenManager",
    "PasswordManager", 
    "AuthenticationError",
    "get_current_user",
    "get_current_user_optional",
    "authenticate_user"
]