"""登录/注销接口"""

from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel, Field
from enum import Enum
import hashlib
import jwt
import bcrypt
from datetime import datetime, timedelta
from backend.api.v1.services.maternal_service import MaternalService

router = APIRouter(tags=["认证管理"])
maternal_service = MaternalService()

JWT_SECRET = "ad09ba2a7ede8fedb9fcf5a6b482c5e4"
JWT_EXPIRATION_DELTA = 86400

class UserType(str, Enum):
    """"用户类型枚举"""
    DOCTOR = "doctor"
    PREGNANT_MOTHER = "pregnant_mother"

class RegisterRequest(BaseModel):
    """注册请求参数模型"""
    username: str = Field(..., description="用户名(不可重复)")
    password: str = Field(..., description="用户密码")
    user_type: UserType = Field(..., description="用户类型")

class LoginRequest(BaseModel):
    """登录请求参数"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="用户密码")

def generate_token(user_id: str) -> str:
    """生成JWT令牌"""
    payloed = {
        "user_id": user_id,
        "exp": datetime.now() + timedelta(seconds = JWT_EXPIRATION_DELTA),
        "iat": datetime.now()
    }
    return jwt.encode(payloed, JWT_SECRET, algorithm="HS256")

def verify_token(token: str) -> str | None:
    """验证JWT令牌， 返回用户ID或None"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# 注册接口（使用Pydantic模型自动校验请求）
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest):
    """用户接口注册"""
    username, password, user_type = request.username, request.password, request.user_type

    existing_user = maternal_service.get_user_info_by_username(username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已被注册"
        )

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode()

    try:
        user = maternal_service.create_user_info(
            username=username,
            password=password_hash,
            user_type=user_type.value
        )
        return {
            "status": "success",
            "message": "注册成功",
            "user_id": user['id']
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败：{str(e)}"
        )

@router.post("/login")
def login(request: LoginRequest):
    username, password = request.username, request.password

    user = maternal_service.get_user_info_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    try:
        stored_password_hash = user['password_hash'] if isinstance(user, dict) else user.password_hash
        is_password_vaild = bcrypt.checkpw(
            password= password.encode('utf-8'),
            hashed_password= stored_password_hash.encode('utf-8')
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"密码验证失败：{str(e)}"
        )
    if not is_password_vaild:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    token = generate_token(username)

    return {
        "status": "success",
        "message": "登录成功",
        "token": token,
        "user_id": user['id'],
        "user_type": user['user_type'] if isinstance(user, dict) else user.user_type
    }

@router.post('/logout')
def logout():
    return {
        "status": "success",
        "message": "注销成功(请客户端删除本地令牌)"
    }

@router.get("/verify")
def verify_auth(request: Request):
    """验证当前用户认证状态（从Authorization头获取Bearer令牌）"""
    # 获取令牌（处理Bearer前缀）
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供有效的认证令牌（需Bearer格式）"
        )
    token = auth_header.replace("Bearer ", "")

    # 验证令牌
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期"
        )

    return {
        "status": "success",
        "message": "认证有效",
        "user_id": user_id
    }