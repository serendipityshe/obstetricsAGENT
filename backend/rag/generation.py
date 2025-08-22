'''
调用llm根据多方结果（rag、文档）生成答案

'''

from typing import Dict, Any, Optional, List
from langchain.schema import SystemMessage, HumanMessage
from langchain_community.chat_message_histories import ChatMessageHistory

from backend.llm.openai_wrapper import QwenAIWrap
from backend.prompt_engineering.strategies.template_selector import TemplateSelector


class RAGLLMGeneration:
    '''
    rag-llm模型生成类
    Args:
        retrieval (RAGRetrieval): rag检索类
        llm (QwenAIWrap): llm模型类
        prompt_settings (PromptSettings): 提示模板类
    Returns:
        Dict[str, Any]: 模型输出
    '''
    def __init__(self, history : ChatMessageHistory = None, document_content : Optional[str] = None) -> None:
        self.llm = QwenAIWrap()
        self.template_selector = TemplateSelector()
        self.history = history

    def filter_content(self, retrieval_docs, document_content):
        '''
        对多方文档内容进行过滤，返回主要内容
        Args:
            retrieval_docs (List[Document]): rag检索到的文档
            document_content (str): 上传的文档内容
        Returns:
            str: 过滤后的文档内容
        '''
        pass

    def generate(self,
        query : str,
        knowledge_fragments: List[dict],
        user_type : str = 'doctor',
        model : Optional[str] = None,
        image : Optional[str] = None,
    ) -> Dict[str, Any]:
        context = "\n\n".join([
            f"文档来源：{frag['source']}, 优先级：{frag['priority']}\n内容：{frag['content']}"
            for frag in knowledge_fragments
        ])


        template = self.template_selector.select_template(user_type, query)
        system_prompt = template['messages'][0]['content']
        rag_prompt = system_prompt.format(context=context, query=query)
        temperature = template['modelParameters']['temperature']
        model_name = template['model']


        # 创建消息列表
        messages = [SystemMessage(content=system_prompt)]

        # 处理图片和文本
        if image:
            # 如果有图片，创建包含图片和文本的多模态消息
            human_content = [
                {"type": "text", "text": rag_prompt},
                {"type": "image_url", "image_url": {"url": image}}
            ]
        else:
            human_content = rag_prompt
        # 只有文本
        messages.append(HumanMessage(content=human_content))

        # 添加历史记录（如果有）
        if self.history and hasattr(self.history, 'messages'):
            messages = self.history.messages + messages

        response = self.llm.invoke(
            input = messages,
            temperature = temperature,
            model=model_name or self.llm.llm_model,
        )

        return response.content