"""问答交互接口"""
from flask import Blueprint, request, jsonify, session
from backend.api.v1.services.chat_service import ChatService
import os

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')
chat_service = ChatService()

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
        
        # 获取上传的文件对象
        uploaded_file = request.files.get('file')
        
        # 调用服务处理问答答（文件处理逻辑已迁移到service层）
        result = chat_service.handle_qa_request(
            session_id=session_id,
            query=query,
            user_type=user_type,
            uploaded_file=uploaded_file  # 直接传递文件对象给服务层处理
        )
        
        return jsonify({
            'status': 'success',** result
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