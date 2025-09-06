import datetime
from fastapi import APIRouter, HTTPException, UploadFile, status, File, Depends, Form, Path  # 新增导入Path
from pydantic import BaseModel, Field
from backend.api.v1.services.maternal_service import MaternalService

# 基础配置
router = APIRouter(tags=["数据库管理"])
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
    upload_time: datetime.datetime
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
    

