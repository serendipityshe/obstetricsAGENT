from flask_restx import Api, Resource, fields, Namespace
from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix
import sys
from pathlib import Path

# 添加项目根目录到系统路径
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# 初始化Flask应用
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)  # 支持代理环境
app.secret_key = 'ad09ba2a7ede8fedb9fcf5a6b482c5e4'

# 创建API实例
api = Api(
    app,
    title='产科智能助手 API',
    version='1.0',
    description='产科智能助手的RESTful API接口文档',
    doc='/docs/',
    security='Bearer Auth'  # 全局认证方式
)

# ==================== 认证命名空间 ====================
auth_ns = Namespace('auth', description='用户认证相关接口')

# 认证请求模型
auth_request = auth_ns.model('AuthRequest', {
    'username': fields.String(required=True, description='用户名'),
    'password': fields.String(required=True, description='密码'),
    'user_type': fields.String(description='用户类型', enum=['doctor', 'patient'])
})

# 认证响应模型
auth_response = auth_ns.model('AuthResponse', {
    'status': fields.String(description='状态', enum=['success', 'error']),
    'message': fields.String(description='消息'),
    'token': fields.String(description='JWT令牌')
})

@auth_ns.route('/register')
class Register(Resource):
    @auth_ns.expect(auth_request)
    @auth_ns.response(201, '注册成功', auth_response)
    @auth_ns.response(400, '参数错误')
    @auth_ns.response(500, '服务器错误')
    def post(self):
        """用户注册接口"""
        return {'status': 'success', 'message': '注册成功'}

@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(auth_request)
    @auth_ns.response(200, '登录成功', auth_response)
    @auth_ns.response(401, '认证失败')
    @auth_ns.response(500, '服务器错误')
    def post(self):
        """用户登录接口"""
        return {'status': 'success', 'message': '登录成功', 'token': 'jwt_token'}

@auth_ns.route('/logout')
class Logout(Resource):
    @auth_ns.response(200, '登出成功')
    @auth_ns.response(500, '服务器错误')
    def post(self):
        """用户登出接口"""
        return {'status': 'success', 'message': '登出成功'}

@auth_ns.route('/verify')
class Verify(Resource):
    @auth_ns.response(200, '验证成功')
    @auth_ns.response(401, '令牌无效')
    def get(self):
        """验证JWT令牌接口"""
        return {'status': 'success', 'message': '令牌有效'}

# ==================== 对话交互命名空间 ====================
chat_ns = Namespace('chat', description='医疗问答对话接口')

# 问答请求模型
qa_request = chat_ns.model('QARequest', {
    'query': fields.String(required=True, description='查询内容'),
    'user_type': fields.String(description='用户类型', enum=['doctor', 'patient'], default='doctor'),
    'session_id': fields.String(description='会话ID')
})

# 问答响应模型
qa_response = chat_ns.model('QAResponse', {
    'status': fields.String(description='状态'),
    'session_id': fields.String(description='会话ID'),
    'answer': fields.String(description='回答内容'),
    'message': fields.String(description='消息')
})

@chat_ns.route('/new_session')
class NewSession(Resource):
    @chat_ns.response(200, '会话创建成功', qa_response)
    @chat_ns.response(500, '服务器错误')
    def post(self):
        """创建新的对话会话"""
        return {
            'status': 'success',
            'session_id': 'new_session_id',
            'message': '新会话创建成功'
        }

@chat_ns.route('/qa')
class MedicalQA(Resource):
    @chat_ns.expect(qa_request)
    @chat_ns.response(200, '问答成功', qa_response)
    @chat_ns.response(400, '参数错误')
    @chat_ns.response(500, '服务器错误')
    def post(self):
        """处理医疗问答请求"""
        return {
            'status': 'success',
            'session_id': 'session_id',
            'answer': '回答内容',
            'message': '问答成功'
        }

@chat_ns.route('/session/<session_id>/history')
class SessionHistory(Resource):
    @chat_ns.response(200, '获取历史成功')
    @chat_ns.response(404, '会话不存在')
    @chat_ns.response(500, '服务器错误')
    def get(self, session_id):
        """获取指定会话的历史记录"""
        return {
            'status': 'success',
            'session_id': session_id,
            'history': [],
            'length': 0
        }

# ==================== 孕妇信息命名空间 ====================
maternal_ns = Namespace('maternal', description='孕妇信息管理接口')

# 孕妇信息模型
maternal_model = maternal_ns.model('MaternalInfo', {
    'id': fields.Integer(description='ID'),
    'id_card': fields.String(required=True, description='身份证号'),
    'phone': fields.String(description='手机号'),
    'current_gestational_week': fields.Integer(description='当前孕周'),
    'expected_delivery_date': fields.Date(description='预产期'),
    'maternal_age': fields.Integer(description='孕妇年龄')
})

# 孕产史模型
pregnancy_history_model = maternal_ns.model('PregnancyHistory', {
    'pregnancy_count': fields.Integer(description='孕次'),
    'bad_pregnancy_history': fields.String(description='不良孕产史'),
    'delivery_method': fields.String(description='分娩方式')
})

# 健康状况模型
health_condition_model = maternal_ns.model('HealthCondition', {
    'has_hypertension': fields.Boolean(description='是否有高血压'),
    'has_diabetes': fields.Boolean(description='是否有糖尿病'),
    'has_thyroid_disease': fields.Boolean(description='是否有甲状腺疾病'),
    'has_heart_disease': fields.Boolean(description='是否有心脏病'),
    'has_liver_disease': fields.Boolean(description='是否有肝脏疾病'),
    'allergy_history': fields.String(description='过敏史')
})

@maternal_ns.route('')
class MaternalCollection(Resource):
    @maternal_ns.expect(maternal_model)
    @maternal_ns.response(201, '创建成功')
    @maternal_ns.response(400, '参数错误')
    @maternal_ns.response(500, '服务器错误')
    def post(self):
        """创建孕妇信息"""
        return {'status': 'success', 'message': '孕妇信息创建成功'}

    @maternal_ns.response(200, '获取成功')
    @maternal_ns.response(500, '服务器错误')
    def get(self):
        """获取所有孕妇信息"""
        return {'status': 'success', 'count': 0, 'data': []}

@maternal_ns.route('/<int:info_id>')
class MaternalItem(Resource):
    @maternal_ns.response(200, '获取成功')
    @maternal_ns.response(404, '未找到')
    @maternal_ns.response(500, '服务器错误')
    def get(self, info_id):
        """根据ID获取孕妇信息"""
        return {'status': 'success', 'data': {}}

    @maternal_ns.expect(maternal_model)
    @maternal_ns.response(200, '更新成功')
    @maternal_ns.response(404, '未找到')
    @maternal_ns.response(500, '服务器错误')
    def put(self, info_id):
        """更新孕妇信息"""
        return {'status': 'success', 'message': '孕妇信息更新成功'}

    @maternal_ns.response(200, '删除成功')
    @maternal_ns.response(404, '未找到')
    @maternal_ns.response(500, '服务器错误')
    def delete(self, info_id):
        """删除孕妇信息"""
        return {'status': 'success', 'message': '孕妇信息删除成功'}

@maternal_ns.route('/id_card/<id_card>')
class MaternalByIdCard(Resource):
    @maternal_ns.response(200, '获取成功')
    @maternal_ns.response(404, '未找到')
    @maternal_ns.response(500, '服务器错误')
    def get(self, id_card):
        """根据身份证号获取孕妇信息"""
        return {'status': 'success', 'data': {}}

@maternal_ns.route('/<int:maternal_id>/history')
class PregnancyHistoryCollection(Resource):
    @maternal_ns.expect(pregnancy_history_model)
    @maternal_ns.response(201, '添加成功')
    @maternal_ns.response(500, '服务器错误')
    def post(self, maternal_id):
        """添加孕产史记录"""
        return {'status': 'success', 'message': '孕产史添加成功'}

    @maternal_ns.response(200, '获取成功')
    @maternal_ns.response(500, '服务器错误')
    def get(self, maternal_id):
        """获取孕妇的所有孕产史"""
        return {'status': 'success', 'count': 0, 'data': []}

@maternal_ns.route('/<int:maternal_id>/health')
class HealthConditionCollection(Resource):
    @maternal_ns.expect(health_condition_model)
    @maternal_ns.response(201, '添加成功')
    @maternal_ns.response(500, '服务器错误')
    def post(self, maternal_id):
        """添加健康状况记录"""
        return {'status': 'success', 'message': '健康状况添加成功'}

    @maternal_ns.response(200, '获取成功')
    @maternal_ns.response(500, '服务器错误')
    def get(self, maternal_id):
        """获取孕妇的所有健康状况记录"""
        return {'status': 'success', 'count': 0, 'data': []}

# 注册命名空间到API
api.add_namespace(auth_ns, path='/api/v1/auth')
api.add_namespace(chat_ns, path='/api/v1/chat')
api.add_namespace(maternal_ns, path='/api/v1/maternal')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='启动API文档服务')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='服务绑定的IP地址')
    parser.add_argument('--port', type=int, default=8803, help='服务监听的端口号')
    args = parser.parse_args()
    args.port = 8801
    print(f"API文档服务启动: http://{args.host}:{args.port}/docs/")
    app.run(host=args.host, port=args.port, debug=True)