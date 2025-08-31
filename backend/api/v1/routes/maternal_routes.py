"""孕妇信息及用户相关接口"""
import os
import uuid

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
def upload_medical_file(maternal_id):
    """上传医疗文件（接收二进制文件内容，保存到服务器并记录数据库）"""
    try:
        # 1. 获取上传的文件对象（微信小程序上传的二进制文件）
        file = request.files.get('file')
        if not file or file.filename == '':
            return jsonify({'status': 'error', 'message': '未选择文件'}), 400

        # 2. 获取其他表单参数（从 form-data 中获取，而非 JSON）
        file_desc = request.form.get('file_desc')
        check_date_str = request.form.get('check_date')

        # 3. 处理文件存储
        # 3.1 定义存储目录（按孕妇ID分目录）
        base_upload_dir = "uploads/maternal_files"
        user_dir = os.path.join(base_upload_dir, str(maternal_id))
        os.makedirs(user_dir, exist_ok=True)  # 确保目录存在

        # 3.2 生成唯一文件名（避免冲突）
        file_ext = os.path.splitext(file.filename)[1].lower()  # 保留文件后缀
        unique_filename = f"{uuid.uuid4()}{file_ext}"  # 使用UUID生成唯一文件名
        file_path = os.path.join(user_dir, unique_filename)

        # 3.3 保存文件到服务器
        file.save(file_path)

        # 4. 处理日期参数
        check_date = None
        if check_date_str:
            check_date = datetime.strptime(check_date_str, '%Y-%m-%d').date()

        # 5. 获取文件元信息
        file_size = os.path.getsize(file_path)  # 文件大小（字节）
        file_type = file.content_type or file_ext.lstrip('.')  # 文件类型（MIME类型或后缀）

        # 6. 调用服务层，将文件信息存入数据库
        result = maternal_service.create_medical_file(
            maternal_id=maternal_id,
            file_name=file.filename,  # 原始文件名
            file_path=file_path,      # 服务器保存的路径
            file_type=file_type,
            file_size=file_size,
            upload_time=datetime.now(),
            file_desc=file_desc,
            check_date=check_date
        )

        return jsonify({
            'status': 'success',
            'message': '文件上传成功',
            'data': result
        }), 201

    except Exception as e:
        # 出错时清理已保存的文件
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'status': 'error', 'message': f'文件上传失败: {str(e)}'}), 500

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