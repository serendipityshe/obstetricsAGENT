import jwt
import uuid
from datetime import datetime, timedelta

"""认证工具(JWT)"""

def generate_token(user_id):
    """生成JWT令牌（新增唯一标识jti用于黑名单）"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION_DELTA),
        'iat': datetime.utcnow(),
        'jti': str(uuid.uuid4())  # 新增唯一标识，用于注销时加入黑名单
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_token(token):
    """验证Token（先检查黑名单，再验证有效性）"""
    try:
        # 1. 检查Token是否在黑名单中
        if redis_client.get(f"blacklist:{token}"):
            return None
        
        # 2. 验证Token签名和有效期
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload['user_id']
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None