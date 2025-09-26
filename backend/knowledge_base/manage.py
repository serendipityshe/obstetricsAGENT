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
        data_root : Union[str, list],
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

        # 智能设备选择：优先尝试CUDA，如果显存不足则回退到CPU
        device = "cpu"  # 默认使用CPU
        if torch.cuda.is_available():
            try:
                # 检查GPU显存情况
                gpu_memory = torch.cuda.get_device_properties(0).total_memory
                gpu_memory_allocated = torch.cuda.memory_allocated(0)
                gpu_memory_free = gpu_memory - gpu_memory_allocated

                # 如果可用显存大于3GB，使用GPU
                if gpu_memory_free > 3 * 1024**3:  # 3GB
                    device = "cuda"
                    print(f"使用GPU进行嵌入计算，可用显存: {gpu_memory_free / 1024**3:.1f}GB")
                else:
                    print(f"GPU显存不足({gpu_memory_free / 1024**3:.1f}GB < 3GB)，使用CPU进行嵌入计算")
            except Exception as e:
                print(f"GPU检测失败，使用CPU进行嵌入计算: {e}")
        else:
            print("CUDA不可用，使用CPU进行嵌入计算")

        model_kwargs = {"device": device}
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
        # 确保存储目录存在
        os.makedirs(self.persist_directory, exist_ok=True)
        
        if not rebuild and os.path.exists(os.path.join(self.persist_directory, 'chroma.sqlite3')):
            try:
                self.vector_store = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.init_embeddings()
                )
                print("成功加载已存在的向量存储")
                return
            except Exception as e:
                print(f"加载已存在的向量存储失败，重新构建: {e}")
                # 清理GPU缓存，为重建腾出空间
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    print("已清理GPU缓存")
                rebuild = True
        
        # 如果没有数据源或数据源不存在，创建空的向量存储
        if not self.data_root or (
            isinstance(self.data_root, str) and not os.path.exists(self.data_root)
        ) or (
            isinstance(self.data_root, list) and not any(os.path.exists(path) for path in self.data_root)
        ):
            print(f"数据源不存在或为空，创建空的向量存储: {self.data_root}")
            embeddings = self.init_embeddings()
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=embeddings
            )
            return
        
        # 如果数据源是列表，逐个处理
        if isinstance(self.data_root, list):
            documents = []
            for data_path in self.data_root:
                if os.path.exists(data_path):
                    print(f"开始加载文件夹：{data_path}")
                    loader = DocumentLoader(data_path)
                    documents.extend(loader.load())
        else:
            print(f"开始加载文件夹：{self.data_root}")
            loader = DocumentLoader(self.data_root)
            documents = loader.load()

        # 如果没有加载到文档，创建空的向量存储
        if not documents:
            print(f"未加载到任何文档，创建空的向量存储")
            embeddings = self.init_embeddings()
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=embeddings
            )
            return

        print(f"加载完成，共加载{len(documents)}个文档")

        try:
            documents_splits = DocumentParser(documents).split()
            print(f"文档分割完成，共{len(documents_splits)}个片段")

            embeddings = self.init_embeddings()
            self.vector_store = Chroma.from_documents(
                documents_splits,
                embeddings,
                persist_directory=self.persist_directory
            )
            print("向量存储构建完成")

            # 构建完成后清理GPU缓存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                print("已清理GPU缓存")

        except Exception as e:
            print(f"向量存储构建失败: {e}")
            # 如果GPU构建失败，尝试强制使用CPU重试
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                print("尝试使用CPU重新构建向量存储...")
                # 强制使用CPU的嵌入函数
                model_kwargs = {"device": "cpu"}
                encode_kwargs = {"normalize_embeddings": True}
                cfg = self.load_config('./backend/config/model_settings.yaml')
                cpu_embeddings = EmbeddingModel(
                    model_name=cfg['embed_model'],
                    model_kwargs=model_kwargs,
                    encode_kwargs=encode_kwargs,
                    cache_folder=cfg['cache_folder'],
                ).embeddings

                self.vector_store = Chroma.from_documents(
                    documents_splits,
                    cpu_embeddings,
                    persist_directory=self.persist_directory
                )
                print("使用CPU成功构建向量存储")
            else:
                raise e

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


        
