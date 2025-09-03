"""
认证路由 - FastAPI版本
从Flask的auth_routes.py迁移
"""

import sys
from pathlib import Path

# 添加项目根目录到系统路径
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from models.auth import (
    UserLogin, UserRegister, TokenResponse, 
    AuthResponse, UserInfo, ErrorResponse
)
from models import success_response, error_response
from auth import (
    TokenManager, PasswordManager, 
    get_current_user, authenticate_user
)
from backend.api.v1.services.maternal_service import MaternalService

# 创建路由器
router = APIRouter(prefix="/api/v1/auth", tags=["认证"])

# 服务实例
maternal_service = MaternalService()

@router.post("/register", 
            response_model=AuthResponse,
            summary="用户注册",
            description="注册新用户账号")
async def register(user_data: UserRegister):
    """用户注册"""
    try:
        # 基础验证
        if user_data.user_type not in ['doctor', 'pregnant_mother']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户类型无效"
            )

        # 检查用户名是否已存在
        existing_user = maternal_service.get_user_info_by_username(user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已被注册"
            )

        # 密码加密
        password_hash = PasswordManager.get_password_hash(user_data.password)

        # 创建用户
        user = maternal_service.create_user_info(
            username=user_data.username,
            password=password_hash,
            user_type=user_data.user_type
        )
        
        return AuthResponse(
            status="success",
            message="注册成功",
            data=TokenResponse(
                access_token="",  # 注册成功后不直接返回token
                user_id=str(user['id']),
                user_type=user_data.user_type
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败：{str(e)}"
        )

@router.post("/login", 
            response_model=AuthResponse,
            summary="用户登录",
            description="用户登录获取访问令牌")
async def login(user_data: UserLogin):
    """用户登录"""
    try:
        # 验证用户凭据
        user = maternal_service.get_user_info_by_username(user_data.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
        # 验证密码
        if not PasswordManager.verify_password(user_data.password, user['password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
        # 生成访问令牌
        access_token = TokenManager.create_access_token(user_data.username)
        
        return AuthResponse(
            status="success",
            message="登录成功",
            data=TokenResponse(
                access_token=access_token,
                user_id=user_data.username,
                user_type=user.get('user_type', 'doctor')
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败：{str(e)}"
        )

@router.post("/logout",
            summary="用户注销", 
            description="注销当前用户会话")
async def logout(current_user: str = Depends(get_current_user)):
    """用户注销"""
    # 在FastAPI中，注销主要是客户端删除token
    # 如果需要服务端黑名单，可以在这里实现
    return success_response(message="注销成功")

@router.get("/verify",
           response_model=AuthResponse,
           summary="验证认证状态",
           description="验证当前用户的认证状态")
async def verify_auth(current_user: str = Depends(get_current_user)):
    """验证当前用户认证状态"""
    try:
        # 获取用户信息
        user = maternal_service.get_user_info_by_username(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
            
        return AuthResponse(
            status="success",
            message="认证有效",
            data=TokenResponse(
                access_token="",  # 验证时不返回新token
                user_id=current_user,
                user_type=user.get('user_type', 'doctor')
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证失败：{str(e)}"
        )

@router.get("/me",
           response_model=UserInfo,
           summary="获取当前用户信息",
           description="获取当前认证用户的详细信息")
async def get_current_user_info(current_user: str = Depends(get_current_user)):
    """获取当前用户信息"""
    try:
        user = maternal_service.get_user_info_by_username(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
            
        return UserInfo(
            user_id=current_user,
            username=current_user,
            user_type=user.get('user_type', 'doctor')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户信息失败：{str(e)}"
        )