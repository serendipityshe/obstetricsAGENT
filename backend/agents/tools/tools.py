from langchain.tools import tool
from typing import Annotated

import base64
import os
import json
import logging

from backend.rag.retrieval import RAGRetrieval
from backend.knowledge_base.manage import KnowledgeBase
from backend.knowledge_base.loader import DocumentLoader
from backend.llm.openai_wrapper import QwenAIWrap

from langchain.schema import HumanMessage
from pydantic import BaseModel, Field
from typing import Optional, Annotated

# 设置Qwen API调试日志
qwen_logger = logging.getLogger('qwen_api_debug')
qwen_logger.setLevel(logging.DEBUG)
if not qwen_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    qwen_logger.addHandler(handler)


# 定义工具输入模型（可选，用于参数校验，增强可读性）
class QwenToolInput(BaseModel):
    input: str = Field(description="用户的原始问题或文本输入内容")
    img_path: Optional[str] = Field(description="图片路径")
    model_name: Optional[str] = Field(description="Qwen模型名称（如 qwen-max、qwen-plus 等）")
    api_key: Optional[str] = Field(description="访问Qwen模型的API密钥")
    base_url: Optional[str] = Field(description="Qwen模型的API请求地址（如 https://api.example.com/v1）")
    temperature: Optional[float] = Field(description="模型生成的随机性（0.0-1.0，值越高随机性越强）", ge=0.0, le=1.0)

@tool(
    name_or_callable="qwen_tool",
    description="调用Qwen大模型处理文本输入（支持可选图片输入），返回模型生成的响应内容",
    args_schema=QwenToolInput  # 关联输入模型，实现参数校验
)
def qwen_tool(
    input: Annotated[str, "用户的原始问题或文本输入内容"],
    img_path: Annotated[Optional[str], "图片路径（为空时仅传递文本）"],
    model_name: Annotated[Optional[str], "Qwen模型名称（如 qwen-max、qwen-plus）"],
    api_key: Annotated[Optional[str], "访问Qwen模型的API密钥"],
    base_url: Annotated[Optional[str], "Qwen模型的API请求地址"],
    temperature: Annotated[Optional[float], "模型随机性（0.0-1.0，推荐0.7）"]
) -> dict:
    """
    原始的非流式qwen_tool（向后兼容）
    保持原有的实现，避免异步/同步冲突
    """
    # 1. 初始化Qwen模型包装器
    qwen_client = QwenAIWrap(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=1500
    )

    # 2. 构造消息
    message_content = [{"type": "text", "text": input}]

    if img_path and str(img_path).strip():
        message_content.append(
            {"type": "image_url", "image_url": {"url": img_path}}
        )

    messages = [HumanMessage(content=message_content)]

    # 3. 调用模型并处理响应（保持原有逻辑）
    try:
        qwen_logger.debug(f"=== Qwen API 请求开始 ===")
        qwen_logger.debug(f"模型名称: {model_name}")

        response = qwen_client.invoke(messages)

        # 处理流式响应，收集所有chunk
        if hasattr(response, '__iter__') and not isinstance(response, str):
            content = ""
            chunk_count = 0
            for chunk in response:
                chunk_count += 1
                if isinstance(chunk, tuple) and len(chunk) == 2 and chunk[0] == 'content' and chunk[1]:
                    content += str(chunk[1])
                elif hasattr(chunk, "content") and chunk.content:
                    content += str(chunk.content)
            response_content = content.strip()
        else:
            if not response or not hasattr(response, "content") or len(str(response.content).strip()) == 0:
                raise ValueError("Qwen模型返回无效响应（空内容或格式错误）")
            response_content = str(response.content).strip()

        qwen_logger.debug(f"=== Qwen API 请求成功 ===")

        return {
            "content": response_content
        }

    except Exception as e:
        qwen_logger.error(f"Qwen模型调用失败: {str(e)}")
        return {
            "content": "",
            "error": f"AI调用失败: {str(e)}"
        }

# 新增：流式版本的qwen_tool
async def qwen_tool_stream(
    input: Annotated[str, "用户的原始问题或文本输入内容"],
    img_path: Annotated[Optional[str], "图片路径（为空时仅传递文本）"],
    model_name: Annotated[Optional[str], "Qwen模型名称（如 qwen-max、qwen-plus）"],
    api_key: Annotated[Optional[str], "访问Qwen模型的API密钥"],
    base_url: Annotated[Optional[str], "Qwen模型的API请求地址"],
    temperature: Annotated[Optional[float], "模型随机性（0.0-1.0，推荐0.7）"]
):
    """
    流式调用Qwen大模型，实时yield输出内容

    返回：异步生成器，yield每个token
    """
    # 1. 初始化Qwen模型包装器
    qwen_client = QwenAIWrap(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=1500
    )

    # 2. 构造消息
    message_content = [{"type": "text", "text": input}]

    if img_path and str(img_path).strip():
        message_content.append(
            {"type": "image_url", "image_url": {"url": img_path}}
        )

    messages = [HumanMessage(content=message_content)]

    # 3. 流式调用并实时yield
    try:
        qwen_logger.debug(f"=== Qwen API 流式请求开始 ===")
        qwen_logger.debug(f"模型名称: {model_name}")

        # 使用stream方法进行真正的流式调用
        chunk_count = 0
        for chunk in qwen_client.client.stream(messages):  # 直接使用ChatOpenAI的stream方法
            chunk_count += 1

            # LangChain的stream方法返回的是AIMessageChunk对象
            if hasattr(chunk, "content") and chunk.content:
                content_piece = str(chunk.content)
                qwen_logger.debug(f"流式输出chunk {chunk_count}: '{content_piece}'")
                yield content_piece

        qwen_logger.debug(f"流式响应总chunk数: {chunk_count}")

    except Exception as e:
        qwen_logger.error(f"Qwen API 流式调用失败: {str(e)}")
        raise e

def qwen_tool(
    input: Annotated[str, "用户的原始问题或文本输入内容"],
    img_path: Annotated[Optional[str], "图片路径（为空时仅传递文本）"],
    model_name: Annotated[Optional[str], "Qwen模型名称（如 qwen-max、qwen-plus）"],
    api_key: Annotated[Optional[str], "访问Qwen模型的API密钥"],
    base_url: Annotated[Optional[str], "Qwen模型的API请求地址"],
    temperature: Annotated[Optional[float], "模型随机性（0.0-1.0，推荐0.7）"]
) -> dict:
    """
    调用Qwen大模型处理文本输入（支持可选图片输入），返回结构化响应

    核心修改：
    - 仅当img_path有效（非空、非空白）时，才添加图片信息到请求中
    - 空img_path时仅传递文本，避免模型因无效图片参数报错
    """
    # 1. 初始化Qwen模型包装器
    qwen_client = QwenAIWrap(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=1500  # 限制输出长度
    )
    
    # 2. 构造消息（动态判断是否添加图片信息）
    # 先添加必选的文本内容
    message_content = [{"type": "text", "text": input}]
    
    # 仅当img_path有效（非None、非空字符串、非纯空白）时，添加图片信息
    if img_path and str(img_path).strip():
        message_content.append(
            {"type": "image_url", "image_url": {"url": img_path}}
        )
    
    # 组装完整的HumanMessage
    messages = [HumanMessage(content=message_content)]
    
    # 3. 调用模型并处理响应（支持流式和非流式）
    try:
        # 记录请求详情
        qwen_logger.debug(f"=== Qwen API 请求开始 ===")
        qwen_logger.debug(f"模型名称: {model_name}")
        qwen_logger.debug(f"API密钥: {api_key[:10]}...{api_key[-4:] if api_key and len(api_key) > 14 else '未提供'}")
        qwen_logger.debug(f"基础URL: {base_url}")
        qwen_logger.debug(f"温度: {temperature}")
        qwen_logger.debug(f"消息内容: {json.dumps(message_content, ensure_ascii=False, indent=2)}")

        response = qwen_client.invoke(messages)

        # 记录原始响应
        qwen_logger.debug(f"原始响应类型: {type(response)}")
        qwen_logger.debug(f"原始响应内容: {response}")
        qwen_logger.debug(f"响应是否可迭代: {hasattr(response, '__iter__') and not isinstance(response, str)}")

        # 处理流式响应
        if hasattr(response, '__iter__') and not isinstance(response, str):
            # 流式响应，收集所有chunk
            content = ""
            chunk_count = 0
            for chunk in response:
                chunk_count += 1
                qwen_logger.debug(f"流式chunk {chunk_count}: {chunk}")
                # 处理元组格式的chunk: ('content', '实际内容')
                if isinstance(chunk, tuple) and len(chunk) == 2 and chunk[0] == 'content' and chunk[1]:
                    content += str(chunk[1])
                # 处理对象格式的chunk (备用逻辑)
                elif hasattr(chunk, "content") and chunk.content:
                    content += str(chunk.content)
            qwen_logger.debug(f"流式响应总chunk数: {chunk_count}")
            qwen_logger.debug(f"流式响应合并内容: '{content}'")
            response_content = content.strip()
        else:
            # 非流式响应
            qwen_logger.debug(f"非流式响应hasattr(content): {hasattr(response, 'content')}")
            if hasattr(response, "content"):
                qwen_logger.debug(f"响应content属性: '{response.content}'")
                qwen_logger.debug(f"响应content类型: {type(response.content)}")
                qwen_logger.debug(f"响应content长度: {len(str(response.content)) if response.content else 0}")

            if not response or not hasattr(response, "content") or len(str(response.content).strip()) == 0:
                qwen_logger.error(f"Qwen模型返回无效响应 - response: {response}, hasattr: {hasattr(response, 'content') if response else False}")
                raise ValueError("Qwen模型返回无效响应（空内容或格式错误）")
            response_content = str(response.content).strip()

        qwen_logger.debug(f"最终处理后内容: '{response_content}'")
        qwen_logger.debug(f"最终内容长度: {len(response_content)}")

        if not response_content:
            qwen_logger.error("最终响应内容为空")
            raise ValueError("Qwen模型返回空内容")

        qwen_logger.debug(f"=== Qwen API 请求成功 ===")

        # 返回标准化结果
        return {
            "status": "success",
            "content": response_content,
            "model_used": model_name,
            "temperature": temperature,
            "has_image": bool(img_path and str(img_path).strip()),  # 新增：标识是否包含图片
            "content_length": len(response_content)  # 新增：内容长度统计
        }
    except Exception as e:
        # 异常处理
        qwen_logger.error(f"=== Qwen API 请求失败 ===")
        qwen_logger.error(f"异常类型: {type(e)}")
        qwen_logger.error(f"异常信息: {str(e)}")
        qwen_logger.error(f"异常详情: {repr(e)}")
        return {
            "status": "error",
            "content": f"调用Qwen模型失败：{str(e)}",
            "model_used": model_name,
            "has_image": bool(img_path and str(img_path).strip())
        }

@tool(
    name_or_callable="rag_tool",
    description="根据用户问题检索指定知识库获取相关知识",
)
def rag_tool(
    user_query: Annotated[str, "用户的原始问题"], 
    vector_store_path: Annotated[str, "向量存储路径"],
    top_k: Annotated[int, "检索知识库的文档数量"] = 1,
) -> dict:
    """根据用户问题检索指定知识库获取相关知识"""
    try:
        # 处理空向量存储路径的情况
        if not vector_store_path or vector_store_path.strip() == "":
            # 使用默认路径
            retrieval = RAGRetrieval()
        else:
            retrieval = RAGRetrieval(persist_directory=vector_store_path)
            
        docs = retrieval.retrieve(user_query, top_k=top_k)
        knowledge_fragments = [{
            "source": doc.metadata.get('source', 'unknown'),
            "priority": doc.metadata.get('priority', 3),
            "content": doc.page_content
        } for doc in docs]
        return {"knowledge_fragments": knowledge_fragments}
    except Exception as e:
        # 如果检索失败，返回空结果而不是抛出异常
        print(f"检索失败: {e}")
        return {"knowledge_fragments": []}

@tool(
    name_or_callable="docproc_tool",
    description="处理.doc .txt .docx .excel .pdf文件，返回文件内容",
)
def docproc_tool(file_path: Annotated[str, "文件路径"]) -> dict:
    """处理.doc .txt .docx .excel .pdf .json文件，返回文件内容"""
    loader = DocumentLoader(file_path)
    docs = loader.load()
    return {"content": docs}

@tool(
    name_or_callable="imgproc_tool",
    description="处理图片文件，返回base64编码内容（用于大模型解析图片）",
)
def imgproc_tool(file_path: Annotated[str, "图片文件路径"]) -> dict:
    """处理图片文件，返回base64编码内容"""
    try:
        with open(file_path, "rb") as image_file:
            # 读取图片二进制内容并转为base64
            base64_str = base64.b64encode(image_file.read()).decode("utf-8")
        return {
            "status": "success",
            "content": base64_str,
            "file_path": file_path
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"图片处理失败: {str(e)}"
        }
    

@tool(
    name_or_callable="save_memory",
    description="将对话记录保存到向量数据库中用于后续的语义检索",
)
def save_memory(chat_history: Annotated[str, "对话记录路径"], persist_directory: Annotated[str, "向量数据库路径"]) -> dict:
    """将对话记录保存到向量数据库中用于后续的语义检索"""
    kb = KnowledgeBase(
        data_root=chat_history,
        persist_directory=persist_directory,
    )
    kb.build_vector_store(rebuild=True)
    return {"status": "success"}
