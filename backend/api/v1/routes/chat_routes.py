"""问答交互接口"""
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from backend.api.v1.services.chat_service import ChatService
import os
import uuid

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')
chat_service = ChatService()

# 配置上传文件路径
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'data', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

@chat_bp.route('/new_session', methods=['POST'])
def new_session():
    """创建新的对话会话"""
    try:
        session_id = chat_service.create_new_session()
        # 将session_id存储到cookie会话中
        session['chat_session_id'] = session_id
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'message': '新会话创建成功'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@chat_bp.route('/qa', methods=['POST'])
def medical_qa():
    """处理医疗问答请求"""
    try:
        # 获取请求参数
        query = request.form.get('query')
        user_type = request.form.get('user_type', 'doctor')
        session_id = request.form.get('session_id') or session.get('chat_session_id')
        
        # 验证必要参数
        if not query:
            return jsonify({'status': 'error', 'message': '查询内容不能为空'}), 400
            
        if not session_id:
            # 如果没有会话ID，创建一个新的
            session_id = chat_service.create_new_session()
            session['chat_session_id'] = session_id
        
        # 处理上传的文件
        uploaded_file = request.files.get('file')
        image_path = None
        document_content = None
        
        if uploaded_file and uploaded_file.filename:
            filename = secure_filename(uploaded_file.filename)
            # 生成唯一文件名避免冲突
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            uploaded_file.save(file_path)
            
            # 根据文件类型处理
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in ['.png', '.jpg', '.jpeg']:
                image_path = file_path
            elif file_ext in ['.pdf', '.docx', '.doc', '.txt']:
                # 处理文档类型
                from backend.knowledge_base.loader import DocumentLoader
                loader = DocumentLoader(file_path)
                documents = loader.load()
                document_content = "\n\n".join([doc.page_content for doc in documents])
        
        # 调用服务处理问答
        result = chat_service.handle_qa_request(
            session_id=session_id,
            query=query,
            user_type=user_type,
            image_path=image_path,
            document_content=document_content
        )
        
        # 清理临时文件
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        if 'file_path' in locals() and os.path.exists(file_path) and file_ext in ['.pdf', '.docx', '.doc', '.txt']:
            os.remove(file_path)
            
        return jsonify({
            'status': 'success',
            **result
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@chat_bp.route('/session/<session_id>/history', methods=['GET'])
def get_session_history(session_id):
    """获取指定会话的历史记录"""
    try:
        history = chat_service.get_session_history(session_id)
        messages = [
            {
                'type': 'human' if isinstance(msg, type(history.messages[0])) and msg.type == 'human' else 'ai',
                'content': msg.content
            }
            for msg in history.messages
        ]
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'history': messages,
            'length': len(messages)
        })
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500