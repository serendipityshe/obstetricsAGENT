"""基于RAGLLM的多模态问答服务封装"""

from typing import Dict, Optional, Any, List
from langchain_community.chat_message_histories import ChatMessageHistory
from backend.rag.generation import RAGLLMGeneration
from backend.rag.retrieval import RAGRetrieval
import time
import os
import base64

class ChatService:
    def __init__(self):
        self.rag_llm = RAGLLMGeneration()
        self.rag_retrieval = RAGRetrieval()  # 用于知识检索
        self.user_sessions = {}  # 存储格式: {session_id: (history, timestamp)}
        self.SESSION_TIMEOUT = 3600  # 会话超时时间(秒)
        self.UPLOAD_DIR = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "..", "..", "..", "..", "data", "uploads"
        )
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

    def _encode_image_to_base64(self, image_path: str) -> str:
        """将图片文件编码为base64格式"""
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            return base64.b64encode(image_data).decode("utf-8")
        except Exception as e:
            raise Exception(f"图片编码失败: {str(e)}")

    def _retrieve_knowledge(self, query: str, document_content: Optional[str] = None) -> List[dict]:
        """融合检索专家知识库和用户文档内容"""
        # 1. 检索专家知识库
        docs = self.rag_retrieval.retrieve(query, top_k=3)
        knowledge_fragments = [
            {
                "source": doc.metadata.get('source', '专家知识库'),
                "priority": doc.metadata.get('priority', 1),
                "content": doc.page_content
            } 
            for doc in docs
        ]
        
        # 2. 若有用户文档，添加到知识片段
        if document_content:
            knowledge_fragments.append({
                "source": "用户上传文档",
                "priority": 2,  # 用户文档优先级高于专家库
                "content": document_content
            })
        
        return knowledge_fragments

    def handle_qa_request(
        self, 
        session_id: str, 
        query: str, 
        user_type: str = 'doctor',
        image_path: Optional[str] = None,
        document_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """处理包含图片和文档的问答请求"""
        try:
            # 获取会话历史
            history = self.get_session_history(session_id)
            
            # 处理图片（转换为base64）
            image_base64 = None
            if image_path and os.path.exists(image_path):
                image_base64 = self._encode_image_to_base64(image_path)
            
            # 检索知识（融合专家库和用户文档）
            knowledge_fragments = self._retrieve_knowledge(query, document_content)
            
            # 设置RAGLLM的会话历史
            self.rag_llm.history = history
            
            # 调用RAGLLM生成回答
            response = self.rag_llm.generate(
                query=query,
                knowledge_fragments=knowledge_fragments,
                user_type=user_type,
                image=f"data:image/png;base64,{image_base64}" if image_base64 else None
            )
            
            # 将当前交互添加到历史记录
            history.add_user_message(query)
            history.add_ai_message(response)
            
            return {
                "answer": response,
                "session_id": session_id,
                "history_length": len(history.messages),
                "sources": [frag["source"] for frag in knowledge_fragments]  # 返回知识来源
            }
        except Exception as e:
            raise Exception(f"处理问答请求失败: {str(e)}")