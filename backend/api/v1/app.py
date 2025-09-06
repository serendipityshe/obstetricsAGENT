import sys
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS
import os

# 添加项目根目录到系统路径
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from backend.api.v1.routes.auth_routes import auth_bp
from backend.api.v1.routes.chat_routes import chat_bp
from backend.api.v1.routes.maternal_routes import maternal_bp

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'ad09ba2a7ede8fedb9fcf5a6b482c5e4')


# 允许所有源地址访问（通配符*）
CORS(app,
     resources={r"/*": {"origins": "*"}},  # 关键修改：使用 * 代替白名单
     supports_credentials=False,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     max_age=3600
)

# 注册所有路由蓝图
app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
app.register_blueprint(chat_bp, url_prefix='/api/v1/chat')
app.register_blueprint(maternal_bp, url_prefix='/api/v1/maternal')


# ===== 添加全局 OPTIONS 处理器 =====
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    response = jsonify()
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
    return response

# ===== 添加 after_request 钩子确保 CORS 头 =====
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8801, debug=True)