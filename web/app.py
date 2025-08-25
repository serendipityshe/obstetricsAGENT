import sys
from pathlib import Path
import time
from threading import Timer
from flask import Flask, request, jsonify, render_template, session
from huggingface_hub import upload_file
from langchain_core.runnables import history
from werkzeug.utils import secure_filename
import os
import uuid
from langchain_community.chat_message_histories import ChatMessageHistory

# 添加项目根目录到系统路径
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))


from backend.agent.core import ObstetricsAgent
from backend.rag.generation import RAGLLMGeneration
from backend.knowledge_base.loader import DocumentLoader

app = Flask(__name__)
app.secret_key = 'ad09ba2a7ede8fedb9fcf5a6b482c5e4'  # 请在生产环境中使用随机生成的安全密钥

obstetrics_agent = ObstetricsAgent()
ragllm_singleton = RAGLLMGeneration()

user_sessions = {}
SESSION_TIMEOUT = 3600

def cleanup_sessions():
    current_time = time.time()
    exprid_ids = [sid for sid, (hist, timestamp) in user_sessions.items() if current_time - timestamp > SESSION_TIMEOUT]
    for sid in exprid_ids:
        del user_sessions[sid]
    Timer(SESSION_TIMEOUT, cleanup_sessions).start()

cleanup_sessions()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/new_conversation', methods=['POST'])
def new_conversation():
    # 清除当前会话ID并创建新会话
    session.pop('session_id', None)
    session_id = str(uuid.uuid4())
    session['session_id'] = session_id
    user_sessions[session_id] = (ChatMessageHistory(), time.time())
    return jsonify({'status': 'success', 'session_id': session_id})


@app.route('/api/qa', methods=['POST'])
def medical_qa():
    query = request.form.get('query')
    user_type = request.form.get('user_type', 'doctor')
    uploaded_file = request.files.get('image')
    image_path = None
    document_content = None

    if not query:
        return jsonify({'error': '查询内容不能为空'}), 400
    
    try:
        session_id = session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
            user_sessions[session_id] = (ChatMessageHistory(), time.time())
        else:
            if session_id not in user_sessions:
                user_sessions[session_id] = (ChatMessageHistory(), time.time())
            else:
                user_sessions[session_id] = (user_sessions[session_id][0], time.time())

        history, _ = user_sessions[session_id]

        # 处理图片上传
        if uploaded_file and uploaded_file.filename:
            # 创建临时目录
            upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            
            # 保存图片
            filename = secure_filename(uploaded_file.filename)
            file_path = os.path.join(upload_dir, filename)
            uploaded_file.save(file_path)

            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in ['.png', '.jpg', '.jpeg']:
                image_path = file_path
            elif file_ext in ['.pdf', '.docx', '.doc', '.txt']:
                loader = DocumentLoader(file_path)
                documents = loader.load()
                document_content = "\n\n".join([doc.page_content for doc in documents])
        
        # 调用RAG模型
        # ragllm_singleton.history = history
        # ragllm_singleton.document_content = document_content
        # response = ragllm_singleton.generate(query=query, image=image_path, user_type=user_type)

        obstetrics_agent.memory.chat_memory = history
        response = obstetrics_agent.invoke(query, user_type=user_type)
        
        # 清理临时文件
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        if 'file_path' in locals() and os.path.exists(file_path) and file_ext in ['.pdf', '.docx', '.doc', '.txt']:
            os.remove(file_path)
        
        return jsonify({
            'answer': response,
            'session_id': session_id,
            'history_length': len(history.messages)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8801)