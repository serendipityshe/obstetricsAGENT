"""Agent调用封装"""

from typing import Dict, Optional, Any
from langchain_community.chat_message_histories import ChatMessageHistory
from backend.agent.core import ObstetricsAgent
from backend.rag.generation import RAGLLMGeneration
import time

class ChatService:
    def __init__(self):
        self.obstetrics_agent = ObstetricsAgent()
        self.rag_llm = RAGLLMGeneration()
        self.user_sessions = {}  # 存储格式: {session_id: (history, timestamp)}
        self.SESSION_TIMEOUT = 3600  # 会话超时时间(秒)

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
        from uuid import uuid4
        session_id = str(uuid4())
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
        document_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """处理问答请求"""
        try:
            # 获取会话历史
            history = self.get_session_history(session_id)
            
            # 设置agent的会话历史
            self.obstetrics_agent.memory.chat_memory = history
            
            # 调用agent处理查询
            response = self.obstetrics_agent.invoke(query, user_type=user_type)
            
            return {
                "answer": response,
                "session_id": session_id,
                "history_length": len(history.messages)
            }
        except Exception as e:
            raise Exception(f"处理问答请求失败: {str(e)}")