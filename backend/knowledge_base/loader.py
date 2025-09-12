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
    
    ARGS:
        file_path : str 文档路径（可以是单个文件或文件夹）.

    RETURN:
        documents : List[Document] 文档列表.
    '''
    def __init__(self, file_path : str):
        self.file_path = file_path


    def _conversation_json_parser(self, data, file_path: str) -> List[Document]:
        """解析列表形式的对话记录JSON：[{"role": "user", "content": "..."}, ...]"""
        if not isinstance(data, list):
            return []
        
        # 过滤并格式化有效消息
        messages = []
        for i, item in enumerate(data):
            # 处理嵌套的对话数据结构
            if isinstance(item, dict):
                # 如果是包含data字段的结构
                if "data" in item and "messages" in item["data"]:
                    nested_messages = item["data"]["messages"]
                    for msg in nested_messages:
                        if isinstance(msg, dict) and "role" in msg and "content" in msg:
                            role = msg["role"]
                            # 处理content可能是列表的情况
                            if isinstance(msg["content"], list):
                                content_text = ""
                                for content_item in msg["content"]:
                                    if isinstance(content_item, dict) and content_item.get("type") == "text":
                                        content_text += content_item.get("text", "")
                                content = content_text
                            else:
                                content = str(msg["content"])
                            
                            if content.strip():  # 只添加非空内容
                                messages.append(f"{role}: {content}")
                # 如果是直接的消息格式
                elif "role" in item and "content" in item:
                    role = item["role"]
                    content = str(item["content"]) if not isinstance(item["content"], str) else item["content"]
                    if content.strip():  # 只添加非空内容
                        messages.append(f"{role}: {content}")
                else:
                    print(f"对话记录中第{i+1}条消息格式不正确，已跳过")
        
        return [Document(
            page_content="\n\n".join(messages),
            metadata={"source": file_path, "message_count": len(messages), "format": "conversation_list"}
        )] if messages else []

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
