'''
知识库协调中枢

TO DO:
1. 协调loader-parse-embedder-vector_store工作流

DONE:

'''

from typing import *
from langchain_chroma import Chroma
from sympy.strategies import rebuild
import yaml
import os

import torch

from langchain_core import documents

from .loader import DocumentLoader
from .parser import DocumentParser
from .embedder import EmbeddingModel
from .vector_store import ChromaVectorStore

class KnowledgeBase:
    '''知识库协调中枢  
    协调loader-parse-embedder-vector_store工作流

    Args:
        data_root (str): 文档加载路径
        persist_directory (str): 向量存储路径
        **kwargs: 其他参数
    Returns:
        List[documents.Document]: 文档列表

    '''
    def __init__(
        self, 
        data_root : str,
        persist_directory : str,
        **kwargs,
    ):

        self.data_root = data_root
        self.persist_directory = persist_directory
        self.kwargs = kwargs
    
    def load_config(self, config_path : str):
        with open(config_path, 'r', encoding= 'utf-8') as f:
            config = yaml.safe_load(f)
        return config

    def init_embeddings(self):
        cfg = self.load_config('./backend/config/model_settings.yaml')
        model_kwargs = {"device": "cuda" if torch.cuda.is_available() else 'cpu'}
        encode_kwargs = {"normalize_embeddings": True}
        return EmbeddingModel(
            model_name=cfg['embed_model'],
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs,
            cache_folder=cfg['cache_folder'],
        ).embeddings

    def build_vector_store(self, rebuild : bool = False):
        '''构建向量存储
        Args:
            rebuild (bool): 是否重新构建向量存储
        
        Returns:
            None
        '''
        if not rebuild and os.path.exists(os.path.join(self.persist_directory, 'chroma.sqlite3')):
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.init_embeddings()
            )
            return
        
        loader = DocumentLoader(self.data_root)
        documents = loader.load()
        documents_splits = DocumentParser(documents).split()
        embeddings = self.init_embeddings()
        self.vector_store = Chroma.from_documents(
            documents_splits,
            embeddings,
            persist_directory=self.persist_directory
        )

    def search(self, query : str, top_k : int = 5):
        '''查询知识库
        
        Args:
            query (str): 查询字符串
            top_k (int): 返回结果数量
        
        Returns:
            返回相似性检索结果
            List[documents.Document]: 文档列表

        '''
        if not self.vector_store:
            self.build_vector_store(rebuild = False)
        return self.vector_store.similarity_search(query, top_k)


        
