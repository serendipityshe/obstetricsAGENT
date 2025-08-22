from langchain.agents import AgentType, initialize_agent, Tool
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from backend.llm.openai_wrapper import QwenAIWrap
from .tools.rag_tool import RAGTool
from .tools.maternal_tool import MaternalTools
from typing import List, Dict, Any
from backend.prompt_engineering.strategies.template_selector import TemplateSelector


class ObstetricsAgent:
    def __init__(self) -> None:
        self.rag_tool = RAGTool().get_tool()
        self.maternal_tools = MaternalTools().get_tool()
        self.tools = [self.rag_tool, self.maternal_tools]
        self.rag_tool_name = self.rag_tool.name
        self.maternal_tool_name = self.maternal_tools.name

        self.llm = QwenAIWrap()
        self.template_selector = TemplateSelector()

        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="output"
        )
        
        # 使用正确的消息类型构建基础提示
        self.base_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="默认系统消息"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            ("ai", "{agent_scratchpad}")
        ])

        # 初始化agent
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
            memory=self.memory,
            verbose=True,
            agent_kwargs={
                "prompt": self.base_prompt,
                "input_variables": ["input", "chat_history", "agent_scratchpad"]
            },
            return_intermediate_steps=True
        )

    def invoke(self, query: str, user_type: str = 'doctor') -> str:
        """处理用户查询的主入口"""
        # 1. 选择提示词模板
        template = self.template_selector.select_template(user_type=user_type, query=query)
        
        # 2. 构建动态系统提示
        dynamic_system_content = self._build_dynamic_system_content(template, user_type, query)
        
        # 3. 更新系统消息
        self.agent.agent.llm_chain.prompt.messages[0] = SystemMessage(content=dynamic_system_content)
        
        # 4. 调用Agent生成回答
        result = self.agent.invoke({"input": query})
        
        return result["output"]

    def _build_dynamic_system_content(self, template: Dict[str, Any], user_type: str, query: str) -> str:
        """构建融合模板内容和工具规则的动态系统提示"""
        # 提取系统消息，确保有默认值
        system_message = next(
            (msg["content"] for msg in template.get("messages", []) if msg.get("role") == "system"),
            "你是一个专业的产科医疗助手，需要使用提供的工具来回答用户问题。"
        )
        print(system_message)
        
        # 处理工具规则
        tool_rules = self._process_tool_rules(template.get("tool_rules", ""))
        print(tool_rules)

        # 提取响应要求并预处理（先处理反斜杠问题）
        response_requirements = template.get("response_requirements", "")
        # 先移除零宽空格，避免在f-string中使用反斜杠
        cleaned_requirements = response_requirements.replace('\u200b', '')
        
        # 合并内容
        full_content = f"【用户类型】{user_type}\n\n"
        full_content += f"{system_message}\n\n"
        full_content += f"【工具调用规则】\n{tool_rules}\n\n"
        if cleaned_requirements:
            full_content += f"【响应要求】{cleaned_requirements}"  # 使用预处理后的变量
        
        return full_content

    def _process_tool_rules(self, template_tool_rules: str) -> str:
        """处理工具规则，模板未定义则使用通用规则"""
        if template_tool_rules.strip():
            return template_tool_rules
        
        # 通用工具规则
        return """1. 知识库查询（疾病知识、指南等）：使用【{}】
2. 计算/功能操作（风险评估等）：使用【{}】
3. 必须基于工具返回结果回答，禁止编造信息
4. 多轮对话中无需重复调用已使用过的工具""".format(self.rag_tool_name, self.maternal_tool_name)

    def clear_memory(self) -> None:
        """清空对话记忆"""
        self.memory.clear()
    