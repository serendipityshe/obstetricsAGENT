'''
云端模型封装

使用QWEN
'''

from typing import Dict, Any, Optional, List, Union, Tuple

from langchain.schema import (
    HumanMessage,
    BaseMessage,
    ChatResult,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.callbacks import (
    CallbackManagerForLLMRun,
)
from langchain_openai import ChatOpenAI
from pydantic import Field

import yaml
from backend.prompt_engineering.strategies.template_selector import TemplateSelector

import base64
import os


class QwenAIWrap(BaseChatModel):
    # 只保留“需要统一管理”或“扩展用”的字段，基础参数通过ChatOpenAI管理
    client: ChatOpenAI = Field(default=None)
    template_selector: TemplateSelector = Field(default_factory=TemplateSelector)  # 用factory避免空初始化

    def __init__(self, 
                 model_name: Optional[str] = None, 
                 api_key: Optional[str] = None, 
                 base_url: Optional[str] = None, 
                 temperature: Optional[float] = None,
                 max_tokens: int = 2048,
                 max_retries: int = 5,
                 **kwargs) -> None:
        super().__init__()
        # 1. 加载默认配置（你的核心新增能力）
        with open('backend/config/model_settings.yaml', 'r', encoding='utf-8') as f:
            model_settings = yaml.safe_load(f)
        default = model_settings['DEFAULT_MODEL']

        # 2. 初始化ChatOpenAI（只转发必要参数，避免冗余）
        self.client = ChatOpenAI(
            api_key=api_key or default['api_key'],
            base_url=base_url or default['base_url'],
            model=model_name or default['llm_model'],
            temperature=temperature if temperature is not None else default['temperature'],
            max_retries=max_retries,
            max_tokens=max_tokens,
            **kwargs
        )

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        # 直接复用ChatOpenAI的标识参数，避免重复定义
        return self.client._identifying_params

    @property
    def _llm_type(self) -> str:
        # 规范返回模型类型（而非具体模型名）
        return "qwen-chat"

    def _generate(self, 
                 messages: List[BaseMessage], 
                 stop: Optional[List[str]] = None, 
                 run_manager: Optional[CallbackManagerForLLMRun] = None, 
                 **kwargs: Any) -> ChatResult:
        # 2. 处理图片（你的核心新增能力）
        processed_msgs = self._process_image_in_message(messages)
        # 3. 转发给ChatOpenAI生成结果
        return self.client._generate(processed_msgs, stop, run_manager, **kwargs)

    def _process_image_in_message(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        # 保留你的图片处理逻辑（核心价值）
        processed = []
        for msg in messages:
            if isinstance(msg, HumanMessage) and isinstance(msg.content, list):
                content = []
                for item in msg.content:
                    if item.get("type") == "image_url":
                        img_path = item["image_url"]["url"]
                        if os.path.exists(img_path):
                            img_type = img_path.split('.')[-1]
                            with open(img_path, "rb") as f:
                                img_b64 = base64.b64encode(f.read()).decode('utf-8')
                            content.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:image/{img_type};base64,{img_b64}"}
                            })
                        else:
                            content.append(item)
                    else:
                        content.append(item)
                processed.append(HumanMessage(content=content))
            else:
                processed.append(msg)
        return processed

        
