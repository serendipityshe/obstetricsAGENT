"""接口文档 - 使用Flask-RESTX生成Swagger文档"""
import sys
from pathlib import Path
from flask import Flask
from flask_restx import Api, Resource, fields
from werkzeug.middleware.proxy_fix import ProxyFix

# 添加项目根目录到系统路径
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# 导入路由蓝图和认证工具
from backend.api.v1.routes.auth_routes import auth_bp
from backend.api.v1.routes.chat_routes import chat_bp
from backend.api.v1.routes.maternal_routes import maternal_bp
from backend.api.common.auth import verify_token

# 初始化Flask应用
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)  # 支持代理环境
app.secret_key = 'ad09ba2a7ede8fedb9fcf5a6b482c5e4'

# 注册蓝图（保持原有路由结构）
app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(maternal_bp)

# 初始化RESTX API
api = Api(
    app,
    version='1.0',
    title='产科智能助手API',
    description='产科智能助手系统的API接口文档',
    doc='/docs/',  # 文档访问路径
    security='Bearer Auth'  # 全局认证方式
)

# 定义命名空间
auth_ns = api.namespace('auth', description='认证相关接口')
chat_ns = api.namespace('chat', description='对话交互接口')
maternal_ns = api.namespace('maternal', description='孕妇信息管理接口')

# 定义通用模型
token_model = api.model('Token', {
    'token': fields.String(description='JWT认证令牌'),
    'user_id': fields.String(description='用户ID')
})

response_model = api.model('Response', {
    'status': fields.String(description='请求状态(success/error)'),
    'message': fields.String(description='提示信息'),
    'data': fields.Raw(description='返回数据', default=None)
})

# 认证相关模型
login_model = api.model('LoginRequest', {
    'username': fields.String(required=True, description='用户名'),
    'password': fields.String(required=True, description='密码')
})

# 对话相关模型
session_model = api.model('Session', {
    'session_id': fields.String(description='对话会话ID')
})

qa_model = api.model('QARequest', {
    'query': fields.String(required=True, description='查询内容'),
    'user_type': fields.String(description='用户类型(doctor/pregnant_mother)', default='doctor'),
    'session_id': fields.String(description='会话ID，不提供则自动创建')
})

# 孕妇信息相关模型
maternal_model = api.model('MaternalInfo', {
    'id_card': fields.String(required=True, description='身份证号'),
    'phone': fields.String(description='联系电话'),
    'current_gestational_week': fields.Integer(description='当前孕周'),
    'expected_delivery_date': fields.Date(description='预产期(YYYY-MM-DD)'),
    'maternal_age': fields.Integer(description='孕妇年龄')
})

# 认证接口文档
@auth_ns.route('/login')
class AuthLogin(Resource):
    @api.expect(login_model)
    @api.marshal_with(api.inherit('LoginResponse', response_model, token_model))
    def post(self):
        """用户登录"""
        pass

@auth_ns.route('/logout')
class AuthLogout(Resource):
    @api.marshal_with(response_model)
    def post(self):
        """用户注销"""
        pass

@auth_ns.route('/verify')
class AuthVerify(Resource):
    @api.marshal_with(api.inherit('VerifyResponse', response_model, {'user_id': fields.String()}))
    def get(self):
        """验证认证状态"""
        pass

# 对话接口文档
@chat_ns.route('/new_session')
class ChatNewSession(Resource):
    @api.marshal_with(api.inherit('NewSessionResponse', response_model, session_model))
    def post(self):
        """创建新对话会话"""
        pass

@chat_ns.route('/qa')
class ChatQA(Resource):
    @api.expect(qa_model)
    @api.marshal_with(api.inherit('QAResponse', response_model, {
        'answer': fields.String(),
        'session_id': fields.String(),
        'history_length': fields.Integer()
    }))
    def post(self):
        """处理医疗问答请求"""
        pass

@chat_ns.route('/session/<string:session_id>/history')
class ChatHistory(Resource):
    @api.marshal_with(api.inherit('HistoryResponse', response_model, {
        'history': fields.List(fields.Raw()),
        'length': fields.Integer()
    }))
    def get(self, session_id):
        """获取会话历史记录"""
        pass

# 孕妇信息接口文档
@maternal_ns.route('')
class MaternalList(Resource):
    @api.expect(maternal_model)
    @api.marshal_with(response_model)
    def post(self):
        """创建孕妇信息"""
        pass

    @api.marshal_with(api.inherit('MaternalListResponse', response_model, {
        'count': fields.Integer(),
        'data': fields.List(fields.Raw())
    }))
    def get(self):
        """获取所有孕妇信息"""
        pass

@maternal_ns.route('/<int:info_id>')
class MaternalDetail(Resource):
    @api.marshal_with(response_model)
    def get(self, info_id):
        """根据ID获取孕妇信息"""
        pass

    @api.expect(maternal_model)
    @api.marshal_with(response_model)
    def put(self, info_id):
        """更新孕妇信息"""
        pass

    @api.marshal_with(response_model)
    def delete(self, info_id):
        """删除孕妇信息"""
        pass

@maternal_ns.route('/id_card/<string:id_card>')
class MaternalByIdCard(Resource):
    @api.marshal_with(response_model)
    def get(self, id_card):
        """根据身份证号获取孕妇信息"""
        pass

@maternal_ns.route('/<int:maternal_id>/history')
class MaternalPregnancyHistory(Resource):
    @api.expect(api.model('PregnancyHistory', {
        'pregnancy_count': fields.Integer(),
        'bad_pregnancy_history': fields.String(),
        'delivery_method': fields.String()
    }))
    @api.marshal_with(response_model)
    def post(self, maternal_id):
        """添加孕产史"""
        pass

@maternal_ns.route('/<int:maternal_id>/health')
class MaternalHealth(Resource):
    @api.expect(api.model('HealthCondition', {
        'has_hypertension': fields.Boolean(),
        'has_diabetes': fields.Boolean(),
        'has_thyroid_disease': fields.Boolean(),
        'has_heart_disease': fields.Boolean(),
        'has_liver_disease': fields.Boolean(),
        'allergy_history': fields.String()
    }))
    @api.marshal_with(response_model)
    def post(self, maternal_id):
        """添加健康状况"""
        pass

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='启动API文档服务')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='服务绑定的IP地址')
    parser.add_argument('--port', type=int, default=8803, help='服务监听的端口号')
    args = parser.parse_args()
    
    print(f"API文档服务启动: http://{args.host}:{args.port}/docs/")
    app.run(host=args.host, port=args.port, debug=True)