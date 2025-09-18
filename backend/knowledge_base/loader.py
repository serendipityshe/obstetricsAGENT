import os
import tempfile
import subprocess
from typing import *
import json

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    CSVLoader,
    UnstructuredWordDocumentLoader,
    JSONLoader
)
from langchain_unstructured import UnstructuredLoader
from langchain.schema import Document

class DocumentLoader:
    '''
    文档加载器，支持单个文件和文件夹路径
    
backend/agents    ARGS:
        file_path : str 文档路径（可以是单个文件或文件夹）.

    RETURN:
        documents : List[Document] 文档列表.
    '''
    def __init__(self, file_path : str):
        self.file_path = file_path


    def _conversation_json_parser(self, data, file_path: str) -> List[Document]:
        """解析各种格式的对话记录JSON"""
        messages = []
        
        try:
            # 处理工作流响应格式：{"data": {"messages": [...]}}
            if isinstance(data, dict) and "data" in data:
                if "messages" in data["data"]:
                    self._extract_messages_from_array(data["data"]["messages"], messages)
                elif "message_list" in data["data"]:
                    self._extract_messages_from_array(data["data"]["message_list"], messages)
            # 处理直接的消息数组格式：[{"role": "user", "content": "..."}, ...]
            elif isinstance(data, list):
                self._extract_messages_from_array(data, messages)
            # 处理单个对话记录格式
            elif isinstance(data, dict) and "role" in data and "content" in data:
                self._extract_single_message(data, messages)
            else:
                print(f"未识别的对话记录格式，文件: {file_path}")
                return []
                
        except Exception as e:
            print(f"解析对话记录时出错，文件: {file_path}，错误: {e}")
            return []
        
        return [Document(
            page_content="\n\n".join(messages),
            metadata={"source": file_path, "message_count": len(messages), "format": "conversation_list"}
        )] if messages else []
    
    def _extract_messages_from_array(self, message_array, messages):
        """从消息数组中提取消息内容"""
        for i, item in enumerate(message_array):
            try:
                self._extract_single_message(item, messages)
            except Exception as e:
                print(f"对话记录中第{i+1}条消息格式不正确，已跳过，错误: {e}")
                continue
    
    def _extract_single_message(self, item, messages):
        """提取单条消息内容"""
        if not isinstance(item, dict) or "role" in item and "content" in item:
            role = item.get("role", "unknown")
            content = item.get("content", "")
            
            # 处理content为列表的情况（多模态内容）
            if isinstance(content, list):
                content_text = ""
                for content_item in content:
                    if isinstance(content_item, dict):
                        if content_item.get("type") == "text":
                            content_text += content_item.get("text", "")
                        elif content_item.get("type") == "image_url":
                            content_text += f"[图片: {content_item.get('image_url', {}).get('file_name', '未知图片')}]"
                        elif content_item.get("type") == "document":
                            content_text += f"[文档: {content_item.get('document', {}).get('file_name', '未知文档')}]"
                content = content_text
            else:
                content = str(content)
            
            if content and content.strip():
                messages.append(f"{role}: {content.strip()}")

    def _original_json_parser(self, data, file_path: str) -> List[Document]:
        """处理原始JSON格式"""
        if not isinstance(data, list):
            return []
        
        return [Document(
            page_content=f"标题：{item.get('title', '')}\n描述：{item.get('metaDescription', '')}\n{''.join(item.get('dataText', [])) if isinstance(item.get('dataText'), list) else str(item.get('dataText', ''))}",
            metadata={"source": file_path, "title": item.get('title', ''), "metaDescription": item.get('metaDescription', '')}
        ) for item in data]

    def _json_loader_func(self, file_path: str) -> List[Document]:
        """加载JSON文件并选择合适的解析器"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"解析JSON文件{file_path}时出错：{e}")
            return []
        
        # 优先使用对话解析器，失败则使用原始解析器
        return self._conversation_json_parser(data, file_path) or self._original_json_parser(data, file_path)

    def _process_single_file(self, file_path: str) -> List[Document]:
        """处理单个文件的加载逻辑"""
        documents = []
        file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')

        # 处理其他支持的文件类型
        loader_map = {
            'pdf' : PyPDFLoader,
            'txt' : TextLoader,
            'csv' : CSVLoader,
            'docx' : UnstructuredLoader,
            'json' : JSONLoader,
            'doc' : UnstructuredLoader,
        }

        if file_ext not in loader_map:
            print(f"不支持的文件类型：{file_ext}")
            return []

        try:
            if file_ext == 'json':
                docs = self._json_loader_func(file_path)
            else:
                loader = loader_map[file_ext](file_path)
                docs = loader.load()
            documents.extend(docs)
        except Exception as e:
            print(f"加载文件{file_path}时出错：{e}")

        return documents

    def load(self) -> List[Document]:
        """加载文档（支持单个文件或文件夹）"""
        documents = []

        # 检查路径是否存在
        if not os.path.exists(self.file_path):
            print(f"错误：路径不存在 - {self.file_path}")
            return documents

        # 处理文件夹（遍历所有文件）
        if os.path.isdir(self.file_path):
            print(f"开始加载文件夹：{self.file_path}")
            for root, _, files in os.walk(self.file_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    documents.extend(self._process_single_file(file_path))
        
        # 处理单个文件
        elif os.path.isfile(self.file_path):
            print(f"开始加载文件：{self.file_path}")
            documents.extend(self._process_single_file(self.file_path))
        
        # 无效路径类型
        else:
            print(f"错误：无效的路径类型 - {self.file_path}")

        print(f"加载完成，共加载{len(documents)}个文档")
        return documents
