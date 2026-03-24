"""
智能体基类

所有智能体的基类，提供：
1. 工具注册和管理
2. 上下文注入（数据库会话、用户信息等）
3. 统一的调用接口
"""

from typing import List, Dict, Any, Optional, Callable
from abc import ABC, abstractmethod
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI


class AgentContext:
    """智能体上下文，存储执行时的环境信息"""

    def __init__(
        self,
        db=None,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        **kwargs
    ):
        self.db = db
        self.user_id = user_id
        self.session_id = session_id
        self.extra = kwargs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "db": self.db,
            "user_id": self.user_id,
            "session_id": self.session_id,
            **self.extra
        }


class BaseAgent(ABC):
    """
    智能体基类

    子类需要实现：
    - name: 智能体名称
    - description: 智能体描述
    - system_prompt: 系统提示词
    - get_tools(): 返回可用工具列表
    """

    name: str = "base_agent"
    description: str = "基础智能体"
    system_prompt: str = "你是一个智能助手。"

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self._tools: List[StructuredTool] = []
        self._context: Optional[AgentContext] = None

    def set_context(self, context: AgentContext):
        """设置执行上下文"""
        self._context = context

    @abstractmethod
    def get_tools(self) -> List[StructuredTool]:
        """返回智能体可用的工具列表"""
        pass

    def bind_tools(self) -> ChatOpenAI:
        """绑定工具到LLM"""
        tools = self.get_tools()
        if tools:
            return self.llm.bind_tools(tools)
        return self.llm

    def _inject_context_to_tools(self):
        """
        将上下文注入到工具函数中

        工具函数通常需要数据库会话等资源，
        这里通过闭包的方式注入。
        """
        if not self._context:
            return

        tools = self.get_tools()
        for tool in tools:
            # 包装工具函数，注入上下文
            original_func = tool.func

            def make_wrapper(func, context):
                def wrapper(*args, **kwargs):
                    # 注入 db 和 user_id
                    if context.db is not None and 'db' not in kwargs:
                        kwargs['db'] = context.db
                    if context.user_id is not None and 'user_id' not in kwargs:
                        kwargs['user_id'] = context.user_id
                    return func(*args, **kwargs)
                return wrapper

            tool.func = make_wrapper(original_func, self._context)

    async def run(self, user_input: str, history: List[Dict] = None) -> Dict[str, Any]:
        """
        运行智能体

        Args:
            user_input: 用户输入
            history: 对话历史

        Returns:
            包含回复内容和可能的工具调用结果
        """
        # 注入上下文
        self._inject_context_to_tools()

        # 构建消息
        messages = [SystemMessage(content=self.system_prompt)]

        # 添加历史
        if history:
            for msg in history:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))

        # 添加当前输入
        messages.append(HumanMessage(content=user_input))

        # 绑定工具
        llm_with_tools = self.bind_tools()

        # 调用LLM
        response = await llm_with_tools.ainvoke(messages)

        result = {
            "content": response.content or "",
            "tool_calls": [],
            "has_tool_call": False
        }

        # 检查工具调用
        if response.tool_calls:
            result["has_tool_call"] = True
            result["tool_calls"] = response.tool_calls

        return result

    async def stream(self, user_input: str, history: List[Dict] = None):
        """
        流式运行智能体

        Yields:
            流式输出的事件
        """
        import json

        # 注入上下文
        self._inject_context_to_tools()

        # 构建消息
        messages = [SystemMessage(content=self.system_prompt)]

        if history:
            for msg in history:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))

        messages.append(HumanMessage(content=user_input))

        # 绑定工具
        llm_with_tools = self.bind_tools()

        # 流式调用
        full_content = ""
        async for chunk in llm_with_tools.astream(messages):
            if chunk.content:
                full_content += chunk.content
                yield {"type": "content", "data": chunk.content}

            # 检查工具调用
            if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                # 工具调用在最后一个chunk中完整返回
                pass

        # 获取完整的工具调用（需要重新调用获取）
        # 由于流式API的限制，我们用完整调用获取工具调用
        if not full_content:
            # 如果没有内容输出，可能有工具调用
            response = await llm_with_tools.ainvoke(messages)
            if response.tool_calls:
                yield {"type": "tool_calls", "data": response.tool_calls}
