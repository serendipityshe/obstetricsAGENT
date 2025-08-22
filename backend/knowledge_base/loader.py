'''
文档加载器

可实现功能：
1. 加载各种文档类型(PDF, CSV, DOC, DOCX, TXT)

已实现功能：
1. 加载PDF, CSV, DOC, DOCX, TXT等文档类型
'''

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
    文档加载器
    
    ARGS:
        file_path : str 文档路径.

    RETURN:
        documents : List[Document] 文档列表.
    '''
    def __init__(self, file_path : str):
        self.file_path = file_path

    def _convert_doc_to_docx(self, doc_path: str) -> str:
        """
        使用 LibreOffice 将 .doc 文件转换为 .docx，并返回临时文件路径
        """
        # 获取文件绝对路径和目录
        absolute_path = os.path.abspath(doc_path)
        dir_name = os.path.dirname(absolute_path)
        file_name = os.path.basename(absolute_path)
        # 生成临时 .docx 文件名（避免覆盖原文件）
        docx_name = os.path.splitext(file_name)[0] + ".docx"
        docx_path = os.path.join(dir_name, docx_name)

        # 调用 LibreOffice 命令行转换（--headless 表示无界面运行）
        try:
            subprocess.run(
                [
                    "libreoffice",
                    "--headless",  # 无界面模式
                    "--convert-to", "docx",  # 转换为 docx 格式
                    "--outdir", dir_name,  # 输出目录
                    absolute_path  # 输入文件路径
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

            # 构建元数据
            metadata = {
                'source' : file_path,
                'title' : item.get('title', ''),
                'metaDescription' : item.get('metaDescription', ''),
            }
            documents.append(Document(page_content = full_text, metadata = metadata))
        return documents

    def load(self) -> List[Document]:
        loader_map = {
            'pdf' : PyPDFLoader,
            'txt' : TextLoader,
            'csv' : CSVLoader,
            'docx' : UnstructuredWordDocumentLoader,
            'json' : JSONLoader,
        }

        documents = []

        for root, _, files in os.walk(self.file_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower().lstrip('.')

                if file_ext == 'doc':
                    # 处理.doc文件：先转换为.docx
                    temp_docx = self._convert_doc_to_docx(file_path)
                    if not temp_docx:
                        print(f"跳过无法转换的.doc文件：{file_path}")
                        continue
                    # 使用docx加载器加载转换后的文件
                    try:
                        loader = UnstructuredWordDocumentLoader(temp_docx)
                        docs = loader.load()
                        # 修正元数据中的source为原.doc文件路径（而非临时文件）
                        for doc in docs:
                            doc.metadata['source'] = file_path
                        documents.extend(docs)
                    finally:
                        os.unlink(temp_docx)  # 无论成功失败都删除临时文件
                    continue

                if file_ext not in loader_map:
                    print(f"不支持的文件类型：{file_ext}")
                    continue

                try:
                    if file_ext == 'json':
                        docs = self._json_loader_func(file_path)
                        documents.extend(docs)
                    else:
                        loader = loader_map[file_ext](file_path)
                        documents.extend(loader.load())
                except Exception as e:
                    print(f"加载文件{file_path}时出错：{e}")

        print(f"共加载了{len(documents)}个文档")
        return documents
        
