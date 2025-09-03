"""
孕妇信息路由 - FastAPI版本
从Flask的maternal_routes.py迁移
"""

import sys
import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# 添加项目根目录到系统路径
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from models.maternal import (
    MaternalInfoCreate, MaternalInfoUpdate, MaternalInfoResponse,
    PregnancyHistoryCreate, PregnancyHistoryResponse,
    HealthConditionCreate, HealthConditionResponse,
    MedicalFileCreate, MedicalFileResponse,
    DialogueCreate, DialogueResponse,
    MaternalResponse, MaternalListResponse,
    PregnancyHistoryListResponse, HealthConditionListResponse,
    MedicalFileListResponse, DialogueListResponse
)
from models import success_response, error_response, list_response
from auth import get_current_user
from config import settings
from backend.api.v1.services.maternal_service import MaternalService

# 创建路由器
router = APIRouter(prefix="/api/v1/maternal", tags=["孕妇信息"])

# 服务实例
maternal_service = MaternalService()

# ==================== 孕妇基本信息接口 ====================

@router.post("",
            response_model=MaternalResponse,
            summary="创建孕妇信息",
            description="创建新的孕妇基本信息记录")
async def create_maternal(
    maternal_data: MaternalInfoCreate,
    current_user: str = Depends(get_current_user)
):
    """创建孕妇信息"""
    try:
        result = maternal_service.create_maternal_info(
            id_card=maternal_data.id_card,
            phone=maternal_data.phone,
            current_gestational_week=maternal_data.current_gestational_week,
            expected_delivery_date=maternal_data.expected_delivery_date,
            maternal_age=maternal_data.maternal_age
        )
        
        return MaternalResponse(
            status="success",
            message="孕妇信息创建成功",
            data=MaternalInfoResponse(**result)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建孕妇信息失败：{str(e)}"
        )

@router.get("/{info_id}",
           response_model=MaternalResponse,
           summary="获取孕妇信息",
           description="根据ID获取孕妇信息")
async def get_maternal(
    info_id: int,
    current_user: str = Depends(get_current_user)
):
    """根据ID获取孕妇信息"""
    try:
        result = maternal_service.get_maternal_info_by_id(info_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到孕妇信息"
            )
            
        return MaternalResponse(
            status="success",
            data=MaternalInfoResponse(**result)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取孕妇信息失败：{str(e)}"
        )

@router.get("/id_card/{id_card}",
           response_model=MaternalResponse,
           summary="根据身份证号获取孕妇信息",
           description="根据身份证号获取孕妇信息")
async def get_maternal_by_id_card(
    id_card: str,
    current_user: str = Depends(get_current_user)
):
    """根据身份证号获取孕妇信息"""
    try:
        result = maternal_service.get_maternal_info_by_id_card(id_card)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到孕妇信息"
            )
            
        return MaternalResponse(
            status="success", 
            data=MaternalInfoResponse(**result)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取孕妇信息失败：{str(e)}"
        )

@router.get("",
           response_model=MaternalListResponse,
           summary="获取所有孕妇信息",
           description="获取所有孕妇信息列表")
async def get_all_maternals(current_user: str = Depends(get_current_user)):
    """获取所有孕妇信息"""
    try:
        results = maternal_service.get_all_maternal_infos()
        
        maternal_list = [MaternalInfoResponse(**result) for result in results]
        
        return MaternalListResponse(
            status="success",
            count=len(maternal_list),
            data=maternal_list
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取孕妇信息列表失败：{str(e)}"
        )

@router.put("/{info_id}",
           response_model=MaternalResponse,
           summary="更新孕妇信息",
           description="更新指定的孕妇信息")
async def update_maternal(
    info_id: int,
    maternal_data: MaternalInfoUpdate,
    current_user: str = Depends(get_current_user)
):
    """更新孕妇信息"""
    try:
        # 转换数据为字典，过滤None值
        update_data = {k: v for k, v in maternal_data.dict().items() if v is not None}
        
        result = maternal_service.update_maternal_info(info_id, **update_data)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到孕妇信息"
            )
            
        return MaternalResponse(
            status="success",
            message="孕妇信息更新成功",
            data=MaternalInfoResponse(**result)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新孕妇信息失败：{str(e)}"
        )

@router.delete("/{info_id}",
              summary="删除孕妇信息",
              description="删除指定的孕妇信息")
async def delete_maternal(
    info_id: int,
    current_user: str = Depends(get_current_user)
):
    """删除孕妇信息"""
    try:
        result = maternal_service.delete_maternal_info(info_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到孕妇信息"
            )
            
        return success_response(message="孕妇信息删除成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除孕妇信息失败：{str(e)}"
        )

# ==================== 孕产史相关接口 ====================

@router.post("/{maternal_id}/history",
            response_model=PregnancyHistoryResponse,
            summary="添加孕产史",
            description="为指定孕妇添加孕产史记录")
async def create_pregnancy_history(
    maternal_id: int,
    history_data: PregnancyHistoryCreate,
    current_user: str = Depends(get_current_user)
):
    """添加孕产史记录"""
    try:
        result = maternal_service.create_pregnancy_history(
            maternal_id=maternal_id,
            pregnancy_count=history_data.pregnancy_count,
            bad_pregnancy_history=history_data.bad_pregnancy_history,
            delivery_method=history_data.delivery_method
        )
        
        return PregnancyHistoryResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加孕产史失败：{str(e)}"
        )

@router.get("/{maternal_id}/history",
           response_model=PregnancyHistoryListResponse,
           summary="获取孕产史",
           description="获取指定孕妇的所有孕产史记录")
async def get_pregnancy_histories(
    maternal_id: int,
    current_user: str = Depends(get_current_user)
):
    """获取孕妇的所有孕产史"""
    try:
        results = maternal_service.get_pregnancy_histories(maternal_id)
        
        history_list = [PregnancyHistoryResponse(**result) for result in results]
        
        return PregnancyHistoryListResponse(
            status="success",
            count=len(history_list),
            data=history_list
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取孕产史失败：{str(e)}"
        )

# ==================== 健康状况相关接口 ====================

@router.post("/{maternal_id}/health",
            response_model=HealthConditionResponse,
            summary="添加健康状况",
            description="为指定孕妇添加健康状况记录")
async def create_health_condition(
    maternal_id: int,
    health_data: HealthConditionCreate,
    current_user: str = Depends(get_current_user)
):
    """添加健康状况记录"""
    try:
        result = maternal_service.create_health_condition(
            maternal_id=maternal_id,
            has_hypertension=health_data.has_hypertension,
            has_diabetes=health_data.has_diabetes,
            has_thyroid_disease=health_data.has_thyroid_disease,
            has_heart_disease=health_data.has_heart_disease,
            has_liver_disease=health_data.has_liver_disease,
            allergy_history=health_data.allergy_history
        )
        
        return HealthConditionResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加健康状况失败：{str(e)}"
        )

@router.get("/{maternal_id}/health",
           response_model=HealthConditionListResponse,
           summary="获取健康状况",
           description="获取指定孕妇的所有健康状况记录")
async def get_health_conditions(
    maternal_id: int,
    current_user: str = Depends(get_current_user)
):
    """获取孕妇的所有健康状况记录"""
    try:
        results = maternal_service.get_health_conditions(maternal_id)
        
        health_list = [HealthConditionResponse(**result) for result in results]
        
        return HealthConditionListResponse(
            status="success",
            count=len(health_list),
            data=health_list
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取健康状况失败：{str(e)}"
        )

# ==================== 医疗文件相关接口 ====================

@router.post("/{maternal_id}/files",
            summary="上传医疗文件",
            description="为指定孕妇上传医疗文件")
async def upload_medical_file(
    maternal_id: int,
    file: UploadFile = File(..., description="医疗文件"),
    file_desc: Optional[str] = Form(None, description="文件描述"),
    check_date: Optional[str] = Form(None, description="检查日期 (YYYY-MM-DD)"),
    current_user: str = Depends(get_current_user)
):
    """上传医疗文件"""
    try:
        # 验证文件
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未选择文件"
            )
            
        # 验证文件大小
        if file.size and file.size > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件大小超过限制({settings.max_file_size // (1024*1024)}MB)"
            )
        
        # 定义存储目录
        base_upload_dir = "uploads/maternal_files"
        user_dir = os.path.join(base_upload_dir, str(maternal_id))
        os.makedirs(user_dir, exist_ok=True)
        
        # 生成唯一文件名
        file_ext = os.path.splitext(file.filename)[1].lower()
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(user_dir, unique_filename)
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 处理日期参数
        check_date_obj = None
        if check_date:
            try:
                check_date_obj = datetime.strptime(check_date, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="日期格式错误，请使用 YYYY-MM-DD 格式"
                )
        
        # 获取文件信息
        file_size = os.path.getsize(file_path)
        file_type = file.content_type or file_ext.lstrip('.')
        
        # 保存到数据库
        result = maternal_service.create_medical_file(
            maternal_id=maternal_id,
            file_name=file.filename,
            file_path=file_path,
            file_type=file_type,
            file_size=file_size,
            upload_time=datetime.now(),
            file_desc=file_desc,
            check_date=check_date_obj
        )
        
        return success_response(
            data=MedicalFileResponse(**result),
            message="文件上传成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # 出错时清理文件
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传失败：{str(e)}"
        )

@router.get("/{maternal_id}/files",
           response_model=MedicalFileListResponse,
           summary="获取医疗文件",
           description="获取指定孕妇的所有医疗文件记录")
async def get_medical_files(
    maternal_id: int,
    current_user: str = Depends(get_current_user)
):
    """获取孕妇的所有医疗文件记录"""
    try:
        results = maternal_service.get_medical_files(maternal_id)
        
        file_list = [MedicalFileResponse(**result) for result in results]
        
        return MedicalFileListResponse(
            status="success",
            count=len(file_list),
            data=file_list
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取医疗文件失败：{str(e)}"
        )

# ==================== 对话记录相关接口 ====================

@router.post("/{maternal_id}/dialogues",
            summary="添加对话记录",
            description="为指定孕妇添加对话记录")
async def create_dialogue(
    maternal_id: int,
    dialogue_data: DialogueCreate,
    current_user: str = Depends(get_current_user)
):
    """添加对话记录"""
    try:
        result = maternal_service.create_dialogue(
            maternal_id=maternal_id,
            dialogue_content=dialogue_data.dialogue_content,
            vector_store_path=dialogue_data.vector_store_path
        )
        
        return success_response(
            data=DialogueResponse(**result),
            message="对话记录添加成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加对话记录失败：{str(e)}"
        )