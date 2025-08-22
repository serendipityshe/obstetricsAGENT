'''
云端模型封装

使用QWEN
'''

from typing import Dict, Any, Optional, List, Union, Tuple

from langchain.schema import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ChatMessage,
    BaseMessage,
    ChatResult,
    ChatGeneration
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import ChatMessageHistory
from pydantic import Field

import yaml
from backend.prompt_engineering.strategies.template_selector import TemplateSelector

import base64
import os

class QwenAIWrap(BaseChatModel):
    '''封装QWEN模型
    Args:

    Return:
        Dict[str, Any]: 模型输出
    '''
    llm_model: str = Field(default=None)
    client: ChatOpenAI = Field(default=None)
    max_retries: int = Field(default=5)
    template_selector: TemplateSelector = Field(default=None)
    api_key: str = Field(default=None)  # 添加api_key字段
    base_url: str = Field(default=None)  # 添加base_url字段
    temperature: float = Field(default=None)  # 添加temperature字段



    def __init__(self, 
            model_name: str = None, 
            api_key: str = None, 
            base_url: str = None, 
            temperature: float = None,
            **kwargs) -> None:


        super().__init__()
        with open('backend/config/model_settings.yaml', 'r', encoding= 'utf-8') as f :
            model_settings = yaml.safe_load(f)
        default_model = model_settings['DEFAULT_MODEL']

        self.llm_model = model_name or default_model['llm_model']
        self.api_key = api_key or default_model['api_key']
        self.base_url = base_url or default_model['base_url']
        self.temperature = temperature if temperature is not None else default_model['temperature']

        self.client = ChatOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            model=self.llm_model,
            max_retries=self.max_retries,
            max_tokens=2048
        )
        self.max_retries = 5
        self.template_selector = TemplateSelector()
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """返回模型的标识参数"""
        return {
            'model' : self.llm_model,
            'temperature' : self.client.temperature,
            'base_url' : self.client.openai_api_base,
        }

    @property
    def _llm_type(self) -> str:
        """返回模型类型"""
        return 'chat-model'

    def _generate(self, messages: list[BaseMessage], stop: Optional[list[str]] = None, run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs: Any) -> ChatResult:
        processed_messages = self._process_image_in_message(messages)

        response = self.client._generate(
            messages=processed_messages,
            stop=stop,
            run_manager=run_manager,
            **kwargs
        )
        return response
    
    def _process_image_in_message(self, messages : List[BaseMessage]) -> List[BaseMessage]:
        """处理消息列表中的图片内容"""
        processed_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage) and isinstance(msg.content, list):
                processed_content = []
                for item in msg.content:
                    if item.get("type") == "image_url":
                        image_url = item["image_url"]["url"]
                        if os.path.exists(image_url):
                            with open(image_url, "rb") as f:
                                image_data = base64.b64encode(f.read()).decode('utf-8')
                            processed_content.append({
                                "type" : "image_rul",
                                "image_url" : {
                                    "url" : f"data:image/png;base64,{image_data}"
                                }
                            })
                        else:
                            processed_content.append(item)
                    else:
                        processed_content.append(item)
                processed_messages.append(HumanMessage(content=processed_content))
            else:
                processed_messages.append(msg)
        return processed_messages

        
