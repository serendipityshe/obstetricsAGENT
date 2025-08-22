from langchain_core.tools import Tool
from backend.rag.retrieval import RAGRetrieval


class RAGTool:
    def __init__(self) -> None:
        self.retrieval = RAGRetrieval()

    def retrieve(self, user_query: str) -> dict:
        """必须使用该工具处理所有用户问题，返回知识库中相关内容。
        
        输入：用户的原始问题；输出：检索到的知识片段+基于知识的初步回答
        """
        docs = self.retrieval.retrieve(user_query, top_k=3)
        knowledge_fragments = [
            {
                "source": doc.metadata.get('source'),
                "priority": doc.metadata.get('priority'),
                "content": doc.page_content
            } 
            for doc in docs
        ]
        return {"knowledge_fragments": knowledge_fragments}

    def get_tool(self) -> Tool:
        return Tool(
            name="rag_tool",  # 工具名更清晰
            func=self.retrieve,
            description="必须首先调用该工具检索知识库，获取与问题相关的知识片段，之后才能回答。输入：用户的原始问题；输出：知识片段列表（含来源和优先级）"
        )
