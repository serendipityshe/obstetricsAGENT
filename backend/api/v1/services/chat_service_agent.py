"""Agent调用封装"""

from typing import Dict, Optional, Any, List
from langchain_community.chat_message_histories import ChatMessageHistory
from backend.agent.core import ObstetricsAgent
from backend.knowledge_base.loader import DocumentLoader
import time
import os
import uuid

class ChatService:
    def __init__(self):
        self.obstetrics_agent = ObstetricsAgent()
        self.user_sessions = {}  # 存储格式: {session_id: (history, timestamp)}
        self.SESSION_TIMEOUT = 3600  # 会话超时时间(秒)
        # 配置上传文件路径
        self.UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'data', 'uploads')
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)

    def _cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = time.time()
        expired_ids = [
            sid for sid, (_, timestamp) in self.user_sessions.items()
            if current_time - timestamp > self.SESSION_TIMEOUT
        ]
        for sid in expired_ids:
            del self.user_sessions[sid]

    def create_new_session(self) -> str:
        """创建新会话"""
        self._cleanup_expired_sessions()
        session_id = str(uuid.uuid4())
        self.user_sessions[session_id] = (ChatMessageHistory(), time.time())
        return session_id

    def get_session_history(self, session_id: str) -> ChatMessageHistory:
        """获取会话历史"""
        self._cleanup_expired_sessions()
        if session_id not in self.user_sessions:
            raise ValueError(f"会话ID不存在: {session_id}")
        
        # 更新会话时间戳
        history, _ = self.user_sessions[session_id]
        self.user_sessions[session_id] = (history, time.time())
        return history

    def handle_qa_request(
        self, 
        session_id: str, 
        query: str, 
        user_type: str = 'doctor',
        image_path: Optional[str] = None,
        document_content: Optional[str] = None,
        uploaded_file: Optional[Any] = None  # 新增：接收上传的文件对象
    ) -> Dict[str, Any]:
        """处理问答请求，整合文件处理逻辑"""
        try:
            # 处理上传文件（如果有）
            processed_image_path = image_path
            processed_doc_content = document_content
            
            if uploaded_file and uploaded_file.filename:
                filename = secure_filename(uploaded_file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                file_path = os.path.join(self.UPLOAD_DIR, unique_filename)
                uploaded_file.save(file_path)
                
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in ['.png', '.jpg', '.jpeg']:
                    processed_image_path = file_path
                elif file_ext in ['.pdf', '.docx', '.doc', '.txt']:
                    loader = DocumentLoader(file_path)
                    documents = loader.load()
                    processed_doc_content = "\n\n".join([doc.page_content for doc in documents])

            # 获取会话历史
            history = self.get_session_history(session_id)
            
            # 设置agent的会话历史
            self.obstetrics_agent.memory.chat_memory = history
            
            # 调用agent处理查询
            response = self.obstetrics_agent.invoke(query, user_type=user_type)
            
            # 清理临时文件
            if processed_image_path and os.path.exists(processed_image_path):
                os.remove(processed_image_path)
            if 'file_path' in locals() and os.path.exists(file_path) and file_ext in ['.pdf', '.docx', '.doc', '.txt']:
                os.remove(file_path)
            
            return {
                "answer": response,
                "session_id": session_id,
                "history_length": len(history.messages)
            }
        except Exception as e:
            raise Exception(f"处理问答请求失败: {str(e)}")

# 辅助函数：安全处理文件名
def secure_filename(filename: str) -> str:
    """确保文件名安全，避免路径遍历攻击"""
    import re
    # 移除文件名中的特殊字符和路径分隔符
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    # 限制文件名长度
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    return filename