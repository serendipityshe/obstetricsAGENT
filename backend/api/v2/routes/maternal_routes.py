from fastapi import APIRouter, Query, UploadFile, status, File, Depends, Form, Path, Body
from typing import Dict, Any, Optional
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
import os
import uuid

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
    has_chronic_disease: bool | None = Field(None, description="是否有慢性病（true/false）")
    chronic_disease_type: str | None = Field(None, description="慢性病类型（如高血压、糖尿病）")
    allergy_history: str | None = Field(None, description="过敏史")
    expected_delivery_date: date | None = Field(None, description="预产期（格式：YYYY-MM-DD）")

    @field_validator('expected_delivery_date')
    def parse_date(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v, "%Y-%m-%d").date()
        return v


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
# @require_auth  # 启用认证（如需关闭可注释）
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
) -> Dict[str, Any]:
    """根据用户ID获取孕妇基本信息"""
    try:
        result = maternal_service.get_maternal_info_by_user_id(user_id)
        return result if result else None
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": f"获取失败：{str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ------------------------------
# 4. 孕产史相关接口
# ------------------------------
@router.put(
    path="/{maternal_id}/pregnancy_history",
    status_code=status.HTTP_200_OK,
    description="更新孕妇孕产史（需认证）"
)
# @require_auth
def update_maternal_pregnancy_history(
    maternal_id: int = Path(..., description="孕妇唯一ID（正整数）"),
    update_data: PregnancyHistoryUpdate = Body(..., description="更新数据")
):
    try:
        result = maternal_service.update_pregnancy_history(
            maternal_id=maternal_id,
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
@router.put(
    path="/{maternal_id}/health_condition",
    status_code=status.HTTP_200_OK,
    description="更新孕妇健康状况（需认证）"
)
# @require_auth
def update_maternal_health_condition(
    maternal_id: int = Path(..., description="孕妇唯一ID（正整数）"),
    update_data: HealthConditionUpdate = Body(..., description="更新数据")
):
    try:
        result = maternal_service.update_health_condition(
            maternal_id=maternal_id,
            **update_data.model_dump(exclude_unset=True)
        )
        
        if not result:
            return JSONResponse(
                content={"status": "error", "message": "未找到该孕妇信息"},
                status_code=status.HTTP_404_NOT_FOUND
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


# ------------------------------
# 6. 医疗文件相关接口
# ------------------------------
@router.post(
    path="/{maternal_id}/files",
    status_code=status.HTTP_201_CREATED,
    description="上传孕妇医疗文件（支持jpg/png/pdf等，需form-data格式）"
)
# @require_auth  # 如需认证可取消注释
def upload_medical_file(
    maternal_id: int = Path(..., description="孕妇唯一ID（正整数）"),
    # 文件参数：FastAPI原生UploadFile，自动处理文件流
    file: UploadFile = File(..., description="上传的医疗文件（必填）"),
    # 表单参数：用Form标注（form-data中的非文件字段）
    file_desc: str | None = Form(None, description="文件描述（可选）"),
    check_date_str: str | None = Form(None, description="检查日期（格式：YYYY-MM-DD，可选）")
):
    try:
        # 1. 验证文件合法性
        if not file.filename:
            return JSONResponse(
                content={"status": "error", "message": "未选择文件或文件名为空"},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 检查文件大小
        file_content = file.file.read()
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            return JSONResponse(
                content={"status": "error", "message": "文件大小不能超过10MB"},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 2. 处理文件存储目录
        base_upload_dir = "uploads/maternal_files"
        user_dir = os.path.join(base_upload_dir, str(maternal_id))
        os.makedirs(user_dir, exist_ok=True)  # 不存在则创建目录

        # 3. 生成唯一文件名（避免冲突）
        file_ext = os.path.splitext(file.filename)[1].lower()  # 提取文件后缀（小写）
        unique_filename = f"{uuid.uuid4()}{file_ext}"  # UUID生成唯一文件名
        file_path = os.path.join(user_dir, unique_filename)

        # 4. 保存文件到服务器（FastAPI UploadFile 需用文件对象保存）
        with open(file_path, "wb") as f:
            f.write(file.file.read())  # 读取上传文件的二进制内容并写入

        # 5. 处理检查日期
        check_date = None
        if check_date_str:
            check_date = datetime.strptime(check_date_str, "%Y-%m-%d").date()

        # 6. 获取文件元信息
        file_size = os.path.getsize(file_path)  # 文件大小（字节）
        file_type = file.content_type or file_ext.lstrip(".")  # 优先用MIME类型，其次后缀

        # 7. 调用业务层保存到数据库
        db_result = maternal_service.create_medical_file(
            maternal_id=maternal_id,
            file_name=file.filename,  # 原始文件名
            file_path=file_path,      # 服务器存储路径
            file_type=file_type,
            file_size=file_size,
            upload_time=datetime.now(),
            file_desc=file_desc,
            check_date=check_date
        )

        # 8. 构造响应（返回关键信息）
        return {
            "status": "success",
            "message": "医疗文件上传成功",
            "data": {
                "file_id": db_result.id if hasattr(db_result, "id") else db_result.get("id"),
                "original_filename": file.filename,
                "storage_path": file_path,
                "file_type": file_type,
                "file_size": file_size,
                "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "check_date": check_date.strftime("%Y-%m-%d") if check_date else None,
                "file_desc": file_desc
            }
        }

    except Exception as e:
        # 出错时清理已保存的文件（避免垃圾文件）
        if "file_path" in locals() and os.path.exists(file_path):
            os.remove(file_path)
        
        return JSONResponse(
            content={"status": "error", "message": f"文件上传失败：{str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    finally:
        # 关闭文件流（避免资源泄漏）
        file.file.close()


@router.get(
    path="/{maternal_id}/files",
    status_code=status.HTTP_200_OK,
    description="获取孕妇的所有医疗文件记录"
)
# @require_auth  # 如需认证可取消注释
def get_medical_files(
    maternal_id: int = Path(description="孕妇唯一ID（正整数）"),
    file_name: str = Query(None, description="文件名称"),
):
    try:
        file_records = maternal_service.get_medical_files(maternal_id, file_name)
        
        return {
            "status": "success",
            "count": len(file_records),
            "data": file_records
        }
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": f"获取文件记录失败：{str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ------------------------------
# 7. 对话记录相关接口
# ------------------------------
@router.post(
    path="/{maternal_id}/dialogues",
    status_code=status.HTTP_201_CREATED,
    description="添加孕妇对话记录"
)
# @require_auth  # 如需认证可取消注释
def create_dialogue(
    maternal_id: int = Path(..., ge=1, description="孕妇唯一ID（正整数）"),
    dialogue_data: DialogueCreate = Body(..., description="对话记录数据")  # 自动解析JSON请求体并验证
):
    try:
        result = maternal_service.create_dialogue(
            maternal_id=maternal_id,
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