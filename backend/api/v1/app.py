
import sys
from pathlib import Path

# 添加项目根目录到系统路径
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from flask import Flask
from backend.api.v1.routes.auth_routes import auth_bp
from backend.api.v1.routes.chat_routes import chat_bp
from backend.api.v1.routes.maternal_routes import maternal_bp

app = Flask(__name__)
app.secret_key = 'ad09ba2a7ede8fedb9fcf5a6b482c5e4'

# 注册所有路由蓝图
app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
app.register_blueprint(chat_bp, url_prefix='/api/v1/chat')
app.register_blueprint(maternal_bp, url_prefix='/api/v1/maternal')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8801)