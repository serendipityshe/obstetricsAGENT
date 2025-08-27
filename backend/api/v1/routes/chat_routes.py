"""问答交互接口"""
from flask import Blueprint, request, jsonify, session
from backend.api.v1.services.chat_service import ChatService
import os
from uuid import uuid4

chat_bp = Blueprint('chat', __name__, url_prefix='/api/v1/chat')
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
    """处理医疗问答请求，支持文件上传"""
    try:
        # 获取请求参数（form-data格式）
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
            # 确保上传目录存在（使用服务层定义的路径）
            upload_dir = chat_service.UPLOAD_DIR
            os.makedirs(upload_dir, exist_ok=True)
            
            # 生成唯一文件名避免冲突
            file_ext = uploaded_file.filename.split('.')[-1].lower() if '.' in uploaded_file.filename else 'bin'
            filename = f"{uuid4()}.{file_ext}"
            file_path = os.path.join(upload_dir, filename)
            
            # 保存文件到本地
            uploaded_file.save(file_path)
            
            # 根据文件类型处理
            if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
                # 图片文件 - 传递路径
                image_path = file_path
            else:
                # 文档文件 - 读取内容（简化处理，实际可能需要解析PDF等）
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        document_content = f.read(10000)  # 限制读取长度
                except UnicodeDecodeError:
                    # 二进制文件处理
                    document_content = f"二进制文件: {uploaded_file.filename} (类型: {file_ext})"
        
        # 调用服务处理问答
        result = chat_service.handle_qa_request(
            session_id=session_id,
            query=query,
            user_type=user_type,
            image_path=image_path,
            document_content=document_content
        )
        
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
                'type': 'human' if msg.type == 'human' else 'ai',
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
