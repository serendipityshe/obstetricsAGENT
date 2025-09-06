from fastapi import APIRouter, HTTPException, UploadFile, status, File, Depends, Form, Path 

router = APIRouter(tags=["聊天管理服务"])

@router.post("/{chat_id}/qa")
async def qa(
    chat_id: str = Path(..., description="聊天ID"),
    question: str = Form(..., description="问题")
):
    """
    问答接口
    """
    return {"chat_id": chat_id, "question": question}
