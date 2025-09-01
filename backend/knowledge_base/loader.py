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
    Docx2txtLoader,
    JSONLoader
)
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

    def _convert_doc_to_docx(self, doc_path: str) -> str:
        """使用 LibreOffice 将 .doc 文件转换为 .docx，并返回临时文件路径"""
        absolute_path = os.path.abspath(doc_path)
        dir_name = os.path.dirname(absolute_path)
        file_name = os.path.basename(absolute_path)
        docx_name = os.path.splitext(file_name)[0] + ".docx"
        docx_path = os.path.join(dir_name, docx_name)

        try:
            subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--convert-to", "docx",
                    "--outdir", dir_name,
                    absolute_path
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f".doc 转换为 .docx 成功：{docx_path}")
            return docx_path
        except subprocess.CalledProcessError as e:
            print(f"转换 .doc 文件失败：{e.stderr.decode('utf-8')}")
            return None

    def _json_loader_func(self, file_path : str):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        documents = []
        for item in data:
            full_text = ''.join(item.get('dataText', []))
            full_text = f"标题：{item.get('title', '')}\n描述：{item.get('metaDescription', '')}\n{full_text}"

            metadata = {
                'source' : file_path,
                'title' : item.get('title', ''),
                'metaDescription' : item.get('metaDescription', ''),
            }
            documents.append(Document(page_content = full_text, metadata = metadata))
        return documents

    def _process_single_file(self, file_path: str) -> List[Document]:
        """处理单个文件的加载逻辑"""
        documents = []
        file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')

        # 处理.doc文件（先转换为docx）
        if file_ext == 'doc':
            temp_docx = self._convert_doc_to_docx(file_path)
            if not temp_docx:
                print(f"跳过无法转换的.doc文件：{file_path}")
                return []
            try:
                loader = UnstructuredWordDocumentLoader(temp_docx)
                docs = loader.load()
                # 修正元数据中的source为原文件路径
                for doc in docs:
                    doc.metadata['source'] = file_path
                documents.extend(docs)
            finally:
                os.unlink(temp_docx)  # 清理临时文件
            return documents

        # 处理其他支持的文件类型
        loader_map = {
            'pdf' : PyPDFLoader,
            'txt' : TextLoader,
            'csv' : CSVLoader,
            'docx' : UnstructuredWordDocumentLoader,
            'json' : JSONLoader,
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
