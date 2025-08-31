"""孕妇信息及用户相关接口"""
from crypt import methods
from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.api.v1.services.maternal_service import MaternalService
from backend.api.common.auth import verify_token, generate_token  # 假设存在令牌生成工具

maternal_bp = Blueprint('maternal', __name__, url_prefix='/api/v1/maternal')
maternal_service = MaternalService()

# ------------------------------
# 孕妇基本信息接口
# ------------------------------
@maternal_bp.route('', methods=['POST'])
@require_auth
def create_maternal():
    """创建孕妇信息"""
    data = request.json
    if 'id_card' not in data:
        return jsonify({'status': 'error', 'message': '身份证号为必填项'}), 400

    try:
        # 解析日期格式
        expected_delivery_date = None
        if 'expected_delivery_date' in data and data['expected_delivery_date']:
            expected_delivery_date = datetime.strptime(data['expected_delivery_date'], '%Y-%m-%d').date()
        
        result = maternal_service.create_maternal_info(
            id_card=data['id_card'],
            phone=data.get('phone'),
            current_gestational_week=data.get('current_gestational_week'),
            expected_delivery_date=expected_delivery_date,
            maternal_age=data.get('maternal_age')
        )
        return jsonify({
            'status': 'success',
            'message': '孕妇信息创建成功',
            'data': result
        }), 201
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
        return jsonify({'status': 'success', 'data': result})
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
        return jsonify({'status': 'success', 'data': result})
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
        # 解析日期字段
        if 'expected_delivery_date' in data and data['expected_delivery_date']:
            data['expected_delivery_date'] = datetime.strptime(
                data['expected_delivery_date'], '%Y-%m-%d').date()
        
        result = maternal_service.update_maternal_info(info_id, **data)
        if not result:
            return jsonify({'status': 'error', 'message': '未找到孕妇信息'}), 404
        return jsonify({
            'status': 'success',
            'message': '孕妇信息更新成功',
            'data': result
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
        return jsonify({'status': 'success', 'message': '孕妇信息删除成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ------------------------------
# 孕产史相关接口
# ------------------------------
@maternal_bp.route('/<int:maternal_id>/history', methods=['POST'])
@require_auth
def create_pregnancy_history(maternal_id):
    """添加孕产史记录"""
    data = request.json
    try:
        result = maternal_service.create_pregnancy_history(
            maternal_id=maternal_id,
            pregnancy_count=data.get('pregnancy_count'),
            bad_pregnancy_history=data.get('bad_pregnancy_history'),
            delivery_method=data.get('delivery_method')
        )
        return jsonify({
            'status': 'success',
            'message': '孕产史添加成功',
            'data': result
        }), 201
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@maternal_bp.route('/<int:maternal_id>/history', methods=['GET'])
@require_auth
def get_pregnancy_histories(maternal_id):
    """获取孕妇的所有孕产史"""
    try:
        results = maternal_service.get_pregnancy_histories(maternal_id)
        return jsonify({
            'status': 'success',
            'count': len(results),
            'data': results
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ------------------------------
# 健康状况相关接口
# ------------------------------
@maternal_bp.route('/<int:maternal_id>/health', methods=['POST'])
@require_auth
def create_health_condition(maternal_id):
    """添加健康状况记录"""
    data = request.json
    try:
        result = maternal_service.create_health_condition(
            maternal_id=maternal_id,
            has_hypertension=data.get('has_hypertension', False),
            has_diabetes=data.get('has_diabetes', False),
            has_thyroid_disease=data.get('has_thyroid_disease', False),
            has_heart_disease=data.get('has_heart_disease', False),
            has_liver_disease=data.get('has_liver_disease', False),
            allergy_history=data.get('allergy_history')
        )
        return jsonify({
            'status': 'success',
            'message': '健康状况添加成功',
            'data': result
        }), 201
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@maternal_bp.route('/<int:maternal_id>/health', methods=['GET'])
@require_auth
def get_health_conditions(maternal_id):
    """获取孕妇的所有健康状况记录"""
    try:
        results = maternal_service.get_health_conditions(maternal_id)
        return jsonify({
            'status': 'success',
            'count': len(results),
            'data': results
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ------------------------------
# 医疗文件相关接口
# ------------------------------
@maternal_bp.route('/<int:maternal_id>/files', methods=['POST'])
@require_auth
def create_medical_file(maternal_id):
    """添加医疗文件记录"""
    data = request.json
    required_fields = ['file_name', 'file_path', 'file_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'status': 'error', 'message': f'缺少必要字段: {field}'}), 400

    try:
        # 解析日期和时间
        upload_time = None
        if 'upload_time' in data and data['upload_time']:
            upload_time = datetime.strptime(data['upload_time'], '%Y-%m-%d %H:%M:%S')
        
        check_date = None
        if 'check_date' in data and data['check_date']:
            check_date = datetime.strptime(data['check_date'], '%Y-%m-%d').date()

        result = maternal_service.create_medical_file(
            maternal_id=maternal_id,
            file_name=data['file_name'],
            file_path=data['file_path'],
            file_type=data['file_type'],
            file_size=data.get('file_size'),
            upload_time=upload_time,
            file_desc=data.get('file_desc'),
            check_date=check_date
        )
        return jsonify({
            'status': 'success',
            'message': '医疗文件记录添加成功',
            'data': result
        }), 201
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@maternal_bp.route('/<int:maternal_id>/files', methods=['GET'])
@require_auth
def get_medical_files(maternal_id):
    """获取孕妇的所有医疗文件记录"""
    try:
        results = maternal_service.get_medical_files(maternal_id)
        return jsonify({
            'status': 'success',
            'count': len(results),
            'data': results
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ------------------------------
# 对话记录相关接口
# ------------------------------
@maternal_bp.route('/<int:maternal_id>/dialogues', methods=['POST'])
@require_auth
def create_dialogue(maternal_id):
    """添加对话记录"""
    data = request.json
    if 'dialogue_content' not in data:
        return jsonify({'status': 'error', 'message': '对话内容为必填项'}), 400

    try:
        result = maternal_service.create_dialogue(
            maternal_id=maternal_id,
            dialogue_content=data['dialogue_content'],
            vector_store_path=data.get('vector_store_path')
        )
        return jsonify({
            'status': 'success',
            'message': '对话记录添加成功',
            'data': result
        }), 201
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500