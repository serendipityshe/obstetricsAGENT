"""孕妇信息相关接口"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.api.v1.services.maternal_service import MaternalService
from backend.api.common.auth import verify_token  # 假设存在此认证工具

maternal_bp = Blueprint('maternal', __name__, url_prefix='/api/v1/maternal')
maternal_service = MaternalService()

# 认证装饰器
def require_auth(f):
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token or not verify_token(token):
            return jsonify({'status': 'error', 'message': '未授权访问'}), 401
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@maternal_bp.route('', methods=['POST'])
@require_auth
def create_maternal():
    """创建孕妇信息"""
    data = request.json
    try:
        # 解析日期
        expected_delivery_date = None
        if 'expected_delivery_date' in data and data['expected_delivery_date']:
            expected_delivery_date = datetime.strptime(data['expected_delivery_date'], '%Y-%m-%d').date()
        
        result = maternal_service.create_maternal_info(
            id_card=data.get('id_card'),
            phone=data.get('phone'),
            current_gestational_week=data.get('current_gestational_week'),
            expected_delivery_date=expected_delivery_date,
            maternal_age=data.get('maternal_age')
        )
        return jsonify({
            'status': 'success',
            'data': result,
            'message': '孕妇信息创建成功'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@maternal_bp.route('/<int:info_id>', methods=['GET'])
@require_auth
def get_maternal(info_id):
    """根据ID获取孕妇信息"""
    try:
        result = maternal_service.get_maternal_info_by_id(info_id)
        if not result:
            return jsonify({'status': 'error', 'message': '未找到孕妇信息'}), 404
        
        return jsonify({
            'status': 'success',
            'data': result
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@maternal_bp.route('/id_card/<id_card>', methods=['GET'])
@require_auth
def get_maternal_by_id_card(id_card):
    """根据身份证号获取孕妇信息"""
    try:
        result = maternal_service.get_maternal_info_by_id_card(id_card)
        if not result:
            return jsonify({'status': 'error', 'message': '未找到孕妇信息'}), 404
        
        return jsonify({
            'status': 'success',
            'data': result
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@maternal_bp.route('', methods=['GET'])
@require_auth
def get_all_maternals():
    """获取所有孕妇信息"""
    try:
        results = maternal_service.get_all_maternal_infos()
        return jsonify({
            'status': 'success',
            'count': len(results),
            'data': results
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@maternal_bp.route('/<int:info_id>', methods=['PUT'])
@require_auth
def update_maternal(info_id):
    """更新孕妇信息"""
    data = request.json
    try:
        # 解析日期
        if 'expected_delivery_date' in data and data['expected_delivery_date']:
            data['expected_delivery_date'] = datetime.strptime(
                data['expected_delivery_date'], '%Y-%m-%d').date()
        
        result = maternal_service.update_maternal_info(info_id, **data)
        if not result:
            return jsonify({'status': 'error', 'message': '未找到孕妇信息'}), 404
        
        return jsonify({
            'status': 'success',
            'data': result,
            'message': '孕妇信息更新成功'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@maternal_bp.route('/<int:info_id>', methods=['DELETE'])
@require_auth
def delete_maternal(info_id):
    """删除孕妇信息"""
    try:
        result = maternal_service.delete_maternal_info(info_id)
        if not result:
            return jsonify({'status': 'error', 'message': '未找到孕妇信息'}), 404
        
        return jsonify({
            'status': 'success',
            'message': '孕妇信息删除成功'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@maternal_bp.route('/<int:maternal_id>/history', methods=['POST'])
@require_auth
def add_pregnancy_history(maternal_id):
    """添加孕产史"""
    data = request.json
    try:
        result = maternal_service.add_pregnancy_history(
            maternal_id=maternal_id,
            pregnancy_count=data.get('pregnancy_count'),
            bad_pregnancy_history=data.get('bad_pregnancy_history'),
            delivery_method=data.get('delivery_method')
        )
        return jsonify({
            'status': 'success',
            'data': result,
            'message': '孕产史添加成功'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@maternal_bp.route('/<int:maternal_id>/health', methods=['POST'])
@require_auth
def add_health_condition(maternal_id):
    """添加健康状况"""
    data = request.json
    try:
        result = maternal_service.add_health_condition(
            maternal_id=maternal_id,** data
        )
        return jsonify({
            'status': 'success',
            'data': result,
            'message': '健康状况添加成功'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500