import jwt
import uuid
from flask import request, jsonify, g
from datetime import datetime, timedelta
from functools import wraps

"""认证工具(JWT)"""

def generate_token(user_id):
    """生成JWT令牌（新增唯一标识jti用于黑名单）"""
    payload = {
        'user_id': user_id,
        'exp': datetime.now() + timedelta(seconds=JWT_EXPIRATION_DELTA),
        'iat': datetime.now(),
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

def require_auth(f):
    """Flask路由装饰器：验证请求中的JWT令牌，未通过则返回401"""
    @wraps(f)  # 保留原函数的名称和文档字符串
    def decorated_function(*args, **kwargs):
        # 1. 从请求头获取Authorization令牌
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'status': 'error',
                'message': '请提供有效的Bearer令牌'
            }), 401
        
        # 2. 提取令牌（去掉"Bearer "前缀）
        token = auth_header.split(' ')[1]
        
        # 3. 验证令牌
        user_id = verify_token(token)
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': '令牌无效或已过期'
            }), 401
        
        # 4. 令牌有效：将用户ID存入全局变量g，供接口函数使用
        g.user_id = user_id
        return f(*args, **kwargs)
    
    return decorated_function