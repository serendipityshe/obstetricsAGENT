'''
嵌入模型

TO DO:
1. 嵌入模型

DONE:
1. 嵌入模型调用
'''

from langchain_huggingface import HuggingFaceEmbeddings

class EmbeddingModel:
    def __init__(self, model_name : str, model_kwargs : dict = None, encode_kwargs : dict = None, cache_folder : str = None):

        self.model_name = model_name
        self.cache_folder = cache_folder
        self.model_kwargs = model_kwargs or {}
        self.encode_kwargs = encode_kwargs or {}
        self.embeddings = HuggingFaceEmbeddings(
            model_name = model_name,
            model_kwargs = self.model_kwargs,
            encode_kwargs = self.encode_kwargs,
            cache_folder = self.cache_folder,
        )


    def embed(self):
        pass