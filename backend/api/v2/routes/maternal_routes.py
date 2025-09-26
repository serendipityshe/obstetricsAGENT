from fastapi import APIRouter, Query, UploadFile, status, File, Depends, Form, Path, Body
from typing import Dict, Any, Optional
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
import os
import uuid
import mimetypes

# 导入业务层和认证依赖（确保路径正确）
from backend.api.v1.services.maternal_service import MaternalService
from backend.api.common.auth import require_auth  # 认证装饰器


# ------------------------------
# 1. 全局配置与依赖初始化
# ------------------------------
router = APIRouter(
    tags=["孕妇数据库管理服务"],  # 统一接口标签（用于API文档分组）
    prefix=""  # 若需统一前缀可在此配置，如 "/api/v1/maternal"
)
maternal_service = MaternalService()  # 初始化业务层实例


# ------------------------------
# 2. Pydantic 模型定义（请求/响应验证）
# ------------------------------
class MaternalInfoUpdate(BaseModel):
    """孕妇基本信息更新请求模型（自动验证+文档生成）"""
    expected_delivery_date: date | None = Field(None, description="预产期（格式：YYYY-MM-DD）")
    # 补充其他可能的字段（如姓名、年龄等），根据实际业务扩展
    phone: str | None = Field(None, description="孕妇电话")
    id_card: str | None = Field(None, description="孕妇身份证号")

    # 可选：自定义日期格式验证（若前端传字符串需额外处理）
    @field_validator('expected_delivery_date')
    def parse_date(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v, "%Y-%m-%d").date()
        return v


class PregnancyHistoryUpdate(BaseModel):
    """孕产史更新请求模型"""
    pregnancy_count: int | None = Field(None, ge=0, description="既往妊娠次数")
    bad_pregnancy_history: str | None = Field(None, description="不良孕产史（非负整数）")
    delivery_method: str | None = Field(None, description="分娩方式（非负整数）")


class HealthConditionUpdate(BaseModel):
    """健康状况更新请求模型"""
    # 根据实际业务补充字段，示例：
    has_hypertension: bool | None = Field(None, description="是否有高血压")
    has_diabetes: bool | None = Field(None, description="是否有糖尿病")
    has_thyroid_disease: bool | None = Field(None, description="是否有甲状腺疾病")
    has_heart_disease: bool | None = Field(None, description="是否有心脏病")
    has_liver_disease: bool | None = Field(None, description="是否有肝脏疾病")
    allergy_history: str | None = Field(None, description="过敏史")


class DialogueCreate(BaseModel):
    """对话记录创建请求模型"""
    dialogue_content: str = Field(..., description="对话内容（必填）")  # ... 表示必填
    vector_store_path: str | None = Field(None, description="向量存储路径（可选）")


# ------------------------------
# 3. 孕妇基本信息接口
# ------------------------------
@router.put(
    path="/{user_id}/info",
    status_code=status.HTTP_200_OK,
    description="更新孕妇基本信息（需认证）"
)
# @require_auth  # 启用认证
def update_maternal_info(
    # 路径参数：用Path标注，添加验证（正整数）和描述
    user_id: int = Path(..., description="孕妇唯一ID（正整数）"),
    # 请求体：用Pydantic模型自动接收JSON数据并验证
    update_data: MaternalInfoUpdate = Body(..., description="更新数据")  # Depends() 自动解析请求体
):
    try:
        print("FastAPI收到的请求数据:", update_data.phone)
        # 将Pydantic模型转为字典，传给业务层（exclude_unset=True 只传有值的字段）
        result = maternal_service.update_maternal_info(
            user_id=user_id,
            **update_data.model_dump(exclude_unset=True)
        )
        print("model_dump结果：", result)
        
        if not result:
            return JSONResponse(
                content={"status": "error", "message": "未找到该孕妇信息"},
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return {
            "status": "success",
            "message": "孕妇基本信息更新成功",
            "data": result  # 假设业务层返回更新后的完整信息
        }
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": f"更新失败：{str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get(
    path = "/{user_id}/get_pregnantMother_info",
    status_code=status.HTTP_200_OK,
    description="获取孕妇基本信息（需认证）"
)
# @require_auth
def get_pregnantMother_info(
    user_id: int = Path(..., description="孕妇唯一ID（正整数）")
):
    """根据用户ID获取孕妇基本信息"""
    try:
        result = maternal_service.get_maternal_info_by_user_id(user_id)
        if not result:
            return JSONResponse(
                content={"status": "error", "message": "未找到该孕妇信息"},
                status_code=status.HTTP_404_NOT_FOUND
            )
        return {
            "status": "success",
            "message": "获取孕妇信息成功",
            "data": result
        }
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": f"获取失败：{str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ------------------------------
# 4. 孕产史相关接口
# ------------------------------

class PregnancyHistoryGetResponse(BaseModel):
    """获取孕妇孕产史响应模型"""
    user_id: int = Field(..., description="孕妇唯一ID（正整数）")
    pregnancy_count: int | None = Field(None, ge=0, description="既往妊娠次数")
    bad_pregnancy_history: str | None = Field(None, description="不良孕产史（非负整数）")
    delivery_method: str | None = Field(None, description="分娩方式（非负整数）")

@router.get(
    path="/{user_id}/pregnancy_history",
    status_code=status.HTTP_200_OK,
    summary="获取孕妇孕产史（需认证）",
    description="获取孕妇孕产史（需认证）"
)
def get_maternal_pregnancy_history(
    user_id: int = Path(..., description="孕妇唯一ID（正整数）")
):
    try:
        result = maternal_service.get_pregnancy_histories(
            maternal_id=user_id
        )
        
        if not result:
            return JSONResponse(
                content={"status": "error", "message": "未找到该孕妇信息"},
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return {
            "status": "success",
            "message": "获取孕产史成功",
            "data": result
        }
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": f"获取失败：{str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.put(
    path="/{user_id}/pregnancy_history",
    status_code=status.HTTP_200_OK,
    description="更新孕妇孕产史（需认证）"
)
# @require_auth
def update_maternal_pregnancy_history(
    user_id: int = Path(..., description="孕妇唯一ID（正整数）"),
    update_data: PregnancyHistoryUpdate = Body(..., description="更新数据")
):
    try:
        result = maternal_service.update_pregnancy_history(
            maternal_id=user_id,
            **update_data.model_dump(exclude_unset=True)
        )
        
        if not result:
            return JSONResponse(
                content={"status": "error", "message": "未找到该孕妇信息"},
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return {
            "status": "success",
            "message": "孕妇孕产史更新成功",
            "data": result
        }
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": f"更新失败：{str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ------------------------------
# 5. 健康状况相关接口
# ------------------------------
class HealthConditionGetResponse(BaseModel):
    """获取孕妇健康状况响应模型"""
    user_id: int = Field(..., description="孕妇唯一ID（正整数）")
    has_hypertension: bool = Field(default=False, description="是否有高血压")
    has_diabetes: bool = Field(default=False, description="是否有糖尿病")
    has_thyroid_disease: bool = Field(default=False, description="是否有甲状腺疾病")
    has_liver_disease: bool = Field(default=False, description="是否有肝脏疾病")
    allergy_history: Optional[str] = Field(default=None, description="过敏史")

@router.get(
    path="/{user_id}/health_condition",
    status_code=status.HTTP_200_OK,
    summary="获取孕妇健康状况（需认证）",
    description="获取孕妇健康状况（需认证）",
    response_model=HealthConditionGetResponse  # 绑定响应模型，自动校验返回格式
)
def get_maternal_health_condition(
    # 直接通过路径参数获取 user_id，用 Path 做校验
    user_id: int = Path(
        ..., 
        ge=1,  # 确保是正整数
        description="孕妇唯一ID（正整数）"
    )
):
    try:
        # 调用服务层获取数据（返回的是列表，需要处理）
        result_list = maternal_service.get_health_conditions(maternal_id=user_id)
        
        if not result_list:
            return JSONResponse(
                content={"detail": "未找到该孕妇信息"},
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # 获取第一条健康状况记录（通常一个孕妇只有一条健康状况记录）
        result = result_list[0] if result_list else None
        if not result:
            return JSONResponse(
                content={"detail": "未找到该孕妇健康状况信息"},
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # 确保返回的数据符合响应模型结构
        return {
            "user_id": user_id,
            "has_hypertension": result.get("has_hypertension", False),
            "has_diabetes": result.get("has_diabetes", False),
            "has_thyroid_disease": result.get("has_thyroid_disease", False),
            "has_heart_disease": result.get("has_heart_disease", False),
            "has_liver_disease": result.get("has_liver_disease", False),
            "allergy_history": result.get("allergy_history")
        }
    
    except Exception as e:
        return JSONResponse(
            content={"detail": f"获取失败：{str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.put(
    path="/{user_id}/health_condition",
    status_code=status.HTTP_200_OK,
    description="更新孕妇健康状况（需认证）"
)
# @require_auth
def update_maternal_health_condition(
    user_id: int = Path(..., description="孕妇唯一ID（正整数）"),
    update_data: HealthConditionUpdate = Body(..., description="更新数据")
):
    """更新孕妇健康状况"""
    try:
        # 先检查健康状况记录是否存在
        existing_conditions = maternal_service.get_health_conditions(user_id)
        
        if not existing_conditions:
            return JSONResponse(
                content={"status": "error", "message": "未找到该孕妇的健康状况记录"},
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        result = maternal_service.update_health_condition(
            maternal_id=user_id,
            **update_data.model_dump(exclude_unset=True)
        )
        
        if not result:
            return JSONResponse(
                content={"status": "error", "message": "更新健康状况失败"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return {
            "status": "success",
            "message": "孕妇健康状况更新成功",
            "data": result
        }
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": f"更新失败：{str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get(
    path="/{user_id}/files/{file_id}/download",
    status_code=status.HTTP_200_OK,
    summary="下载孕妇医疗文件",
    description="根据文件ID下载指定的医疗文件"
)
# @require_auth  # 如需认证可取消注释
def download_medical_file(
    user_id: int = Path(..., description="孕妇唯一ID（正整数）"),
    file_id: int = Path(..., description="文件唯一ID（正整数）")
):
    """下载医疗文件"""
    try:
        # 1. 获取文件信息
        file_info = maternal_service.get_medical_file_by_fileid(str(file_id))
        
        if not file_info:
            return JSONResponse(
                content={"status": "error", "message": "文件不存在"},
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # 2. 验证文件归属权（确保文件属于指定的孕妇）
        if file_info["maternal_id"] != user_id:
            return JSONResponse(
                content={"status": "error", "message": "无权访问该文件"},
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # 3. 检查文件是否存在于服务器
        file_path = file_info["file_path"]
        
        # 4. 安全检查：防止路径遍历攻击
        # 确保文件路径在允许的上传目录范围内
        allowed_base_dir = os.path.abspath("uploads/maternal_files")
        actual_file_path = os.path.abspath(file_path)
        
        if not actual_file_path.startswith(allowed_base_dir):
            return JSONResponse(
                content={"status": "error", "message": "非法文件路径"},
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        if not os.path.exists(file_path):
            return JSONResponse(
                content={"status": "error", "message": "文件在服务器上不存在"},
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # 5. 确定文件的MIME类型
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = "application/octet-stream"  # 默认二进制类型
        
        # 6. 返回文件响应
        return FileResponse(
            path=file_path,
            media_type=mime_type,
            filename=file_info["file_name"],  # 使用原始文件名
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{file_info['file_name']}",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
        )
        
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": f"下载文件失败：{str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ------------------------------
# 7. 对话记录相关接口
# ------------------------------
@router.post(
    path="/{user_id}/dialogues",
    status_code=status.HTTP_201_CREATED,
    description="添加孕妇对话记录"
)
# @require_auth  # 如需认证可取消注释
def create_dialogue(
    user_id: int = Path(..., ge=1, description="孕妇唯一ID（正整数）"),
    dialogue_data: DialogueCreate = Body(..., description="对话记录数据")  # 自动解析JSON请求体并验证
):
    try:
        result = maternal_service.create_dialogue(
            maternal_id=user_id,
            dialogue_content=dialogue_data.dialogue_content,
            vector_store_path=dialogue_data.vector_store_path
        )
        
        return {
            "status": "success",
            "message": "对话记录添加成功",
            "data": result
        }
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": f"添加对话记录失败：{str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )