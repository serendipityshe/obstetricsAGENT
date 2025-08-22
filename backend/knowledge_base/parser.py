'''
文档解析与分块（内容理解和结构化（分块策略））

可实现功能：
1. 文档加载
2. 内容提取
3. 文档结构解析
4. 文本分块
5. 元数据提取与关联
6. 清理与规范化

已实现功能：
1. 文本分块
2. 像元数据中添加[priority]字段用于指定文档优先级
''' 

from langchain.text_splitter import RecursiveCharacterTextSplitter

class DocumentParser:
    def __init__(self, documents):
        self.documents = documents

    def parse(self):
        sources = {
            r'data\raw_manuals\《妇产科学》第10版.pdf' : 1,
            r'data\raw_manuals\孕期知识科普.docx' : 2,
            r'data\raw_manuals\孕前和孕期保健指南.doc' : 3,
        }

        for doc in self.documents:
            if doc.metadata['source'] in sources:
                doc.metadata['priority'] = sources[doc.metadata['source']]
        return self.documents


    def split(self, chunk_size : int = 2000, chunk_overlap : int = 200):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = chunk_size,
            chunk_overlap = chunk_overlap,
        )
        documents = self.parse()
        return text_splitter.split_documents(documents)
        