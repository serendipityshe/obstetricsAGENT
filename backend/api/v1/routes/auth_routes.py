"""登录/注销接口"""
from flask import Blueprint, request, jsonify, session
import hashlib
import time
import jwt
from datetime import datetime, timedelta
# from backend.config.model_settings import FLASK_SECRET_KEY

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# 实际应用中应该从数据库获取用户信息
# 这里仅作为示例
USER_CREDENTIALS = {
    # 密码哈希示例: 实际应该从数据库获取
    'doctor1': hashlib.sha256('password123'.encode()).hexdigest(),
    'admin': hashlib.sha256('adminpass'.encode()).hexdigest()
}

# JWT配置
JWT_SECRET = 'ad09ba2a7ede8fedb9fcf5a6b482c5e4'
JWT_EXPIRATION_DELTA = 86400  # 24小时

def generate_token(user_id):
    """生成JWT令牌"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION_DELTA),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_token(token):
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'status': 'error', 'message': '用户名和密码不能为空'}), 400
    
    # 验证用户
    if username not in USER_CREDENTIALS:
        return jsonify({'status': 'error', 'message': '用户名或密码错误'}), 401
    
    # 验证密码
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if password_hash != USER_CREDENTIALS[username]:
        return jsonify({'status': 'error', 'message': '用户名或密码错误'}), 401
    
    # 生成令牌
    token = generate_token(username)
    
    # 存储会话信息
    session['user_id'] = username
    session['token'] = token
    
    return jsonify({
        'status': 'success',
        'message': '登录成功',
        'token': token,
        'user_id': username
    })

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用户注销"""
    # 清除会话信息
    session.pop('user_id', None)
    session.pop('token', None)
    
    return jsonify({
        'status': 'success',
        'message': '注销成功'
    })

@auth_bp.route('/verify', methods=['GET'])
def verify_auth():
    """验证当前用户认证状态"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'status': 'error', 'message': '未提供认证令牌'}), 401
    
    user_id = verify_token(token)
    if not user_id:
        return jsonify({'status': 'error', 'message': '令牌无效或已过期'}), 401
    
    return jsonify({
        'status': 'success',
        'message': '认证有效',
        'user_id': user_id
    })