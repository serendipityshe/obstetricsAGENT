from fastapi import APIRouter, HTTPException, UploadFile, status, File, Depends, Form, Path  # 新增导入Path
from pydantic import BaseModel, Field
from backend.api.v1.services.maternal_service import MaternalService


"""孕妇信息及用户相关接口"""
import os
import uuid

from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.api.v1.services.maternal_service import MaternalService
from backend.api.common.auth import verify_token, generate_token, require_auth  # 假设存在令牌生成工具

# 基础配置
router = APIRouter(tags=["孕妇数据库管理服务"])
maternal_service = MaternalService()


# 请求参数模型（不变）
class UploadFileRequest(BaseModel):
    chat_id: str = Field(..., description="对话ID（字母/数字/_/-，1-64字符）")

    class Config:
        from_attributes = True
        populate_by_name = True

    @classmethod
    def from_form(cls, chat_id: str = Form(...)):
        return cls(chat_id=chat_id)


# 响应模型（不变）
class UploadSuccessData(BaseModel):
    maternal_id: int
    chat_id: str
    file_id: str
    file_name: str
    save_path: str
    upload_time: datetime
    file_type: str


# 核心接口：修复路径参数标注（Field→Path）
@router.post(
    path="/{maternal_id}/files",
    status_code=status.HTTP_201_CREATED,
    description="无认证版孕妇文件上传接口（修复路径参数报错）"
)
def upload_maternal_file(
    # 关键修复：路径参数必须用Path标注，不能用Field
    maternal_id: int = Path(..., description="母亲唯一ID"),  # 替换Field为Path
    # 文件参数（不变）
    file: UploadFile = File(..., description="上传文件（jpg/png/pdf等）"),
    # Form参数（不变）
    req_params: UploadFileRequest = Depends(UploadFileRequest.from_form),
):
    # 核心功能暂用pass占位
    pass
    

# ------------------------------
# 孕妇基本信息接口
# ------------------------------

@router.put(
    path="/{maternal_id}/info",
    status_code=status.HTTP_200_OK,
)
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


# ------------------------------
# 孕产史相关接口
# ------------------------------
@router.put(
    path="/{maternal_id}/pregnancy_history",
    status_code=status.HTTP_200_OK,
)
@require_auth
def update_maternal(maternal_id):
    """更新孕妇信息"""
    data = request.json
    try:
        # 解析日期字段
        if 'expected_delivery_date' in data and data['expected_delivery_date']:
            data['expected_delivery_date'] = datetime.strptime(
                data['expected_delivery_date'], '%Y-%m-%d').date()
        
        result = maternal_service.update_pregnancy_history(maternal_id, **data)
        if not result:
            return jsonify({'status': 'error', 'message': '未找到孕妇信息'}), 404
        return jsonify({
            'status': 'success',
            'message': '孕妇信息更新成功',
            'data': result
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ------------------------------
# 健康状况相关接口
# ------------------------------
@router.put(
    path="/{maternal_id}/health_condition",
    status_code=status.HTTP_200_OK,
)
@require_auth
def update_maternal(maternal_id):
    """更新孕妇信息"""
    data = request.json
    try:
        # 解析日期字段
        if 'expected_delivery_date' in data and data['expected_delivery_date']:
            data['expected_delivery_date'] = datetime.strptime(
                data['expected_delivery_date'], '%Y-%m-%d').date()
        
        result = maternal_service.update_health_condition(maternal_id, **data)
        if not result:
            return jsonify({'status': 'error', 'message': '未找到孕妇信息'}), 404
        return jsonify({
            'status': 'success',
            'message': '孕妇信息更新成功',
            'data': result
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ------------------------------
# 医疗文件相关接口
# ------------------------------
@router.post(
    path="/{maternal_id}/files",
    status_code=status.HTTP_201_CREATED,
)
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

       # 6. 关键修改：明确返回file_path（结合数据库结果，补充路径）
        return jsonify({
            'status': 'success',
            'message': '文件上传成功',
            'data': {
                # 保留数据库返回的关键信息（如记录ID）
                'file_id': result.id if hasattr(result, 'id') else result.get('id'),
                'original_filename': file.filename,  # 原始文件名
                'storage_path': file_path,  # 明确返回存储路径（核心需求）
                'file_type': file_type,     # 文件类型（如image/jpeg）
                'file_size': file_size,     # 文件大小
                'upload_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 格式化时间
            }
        }), 201

    except Exception as e:
        # 出错时清理已保存的文件
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'status': 'error', 'message': f'文件上传失败: {str(e)}'}), 500

@router.get(
    path="/{maternal_id}/files",
    status_code=status.HTTP_200_OK,
)
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
@router.post(
    path="/{maternal_id}/dialogues",
    status_code=status.HTTP_201_CREATED,
)
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

