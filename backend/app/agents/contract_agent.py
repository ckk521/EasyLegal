"""
法务智能体

专门处理法务咨询和合同相关任务的智能体。

根据 PRD §10.1.3 详细调用流程设计：
1. 消息分类（打招呼/非法务/法务相关）
2. 意图细分（法律咨询/合同状态查询/合同相关）
3. 模板查询结果处理
"""

from typing import List, Dict, Any, Optional
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

from app.agents.base import BaseAgent, AgentContext
from app.agents.tools.contract_tools import create_contract_tools, TOOL_EXECUTORS
from app.agents.prompts.contract_prompts import (
    CONTRACT_AGENT_SYSTEM_PROMPT,
    DEFAULT_GREETING,
    DEFAULT_REJECTION,
)


class ContractAgent(BaseAgent):
    """
    法务智能体

    负责处理法务咨询和合同相关的所有交互。
    """

    name: str = "contract_agent"
    description: str = "法务助理，提供法律咨询和合同相关服务"
    system_prompt: str = CONTRACT_AGENT_SYSTEM_PROMPT

    def __init__(self, llm: ChatOpenAI):
        super().__init__(llm)
        self._tools = create_contract_tools()
        self._greeting: str = DEFAULT_GREETING
        self._rejection: str = DEFAULT_REJECTION

    def set_greeting(self, greeting: str):
        """设置问候语（从数据库配置加载）"""
        self._greeting = greeting

    def set_rejection(self, rejection: str):
        """设置拒绝话术（从数据库配置加载）"""
        self._rejection = rejection

    def get_tools(self) -> List:
        """返回可用工具"""
        return self._tools

    async def process_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理工具调用

        工具调用返回的是 action 标识，这里执行实际的业务逻辑。

        Args:
            tool_call: 工具调用信息，包含 name 和 args

        Returns:
            工具执行结果
        """
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args", {}).copy()

        # 移除 LLM 可能错误注入的参数
        tool_args.pop("db", None)
        tool_args.pop("user_id", None)

        # 获取执行函数
        executor = TOOL_EXECUTORS.get(tool_name)
        if not executor:
            return {
                "success": False,
                "error": f"未找到工具执行器: {tool_name}"
            }

        # 根据工具参数签名注入上下文
        if self._context and self._context.db:
            import inspect
            sig = inspect.signature(executor)
            if "db" in sig.parameters:
                tool_args["db"] = self._context.db
            if "user_id" in sig.parameters:
                tool_args["user_id"] = self._context.user_id

        try:
            result = executor(**tool_args)
            return {
                "success": True,
                "tool_name": tool_name,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "tool_name": tool_name,
                "error": str(e)
            }

    async def run_with_tools(self, user_input: str, history: List[Dict] = None) -> Dict[str, Any]:
        """
        运行智能体并自动处理工具调用

        这是主要的入口方法，会：
        1. 调用LLM获取回复
        2. 如果有工具调用，执行工具
        3. 返回最终结果

        Args:
            user_input: 用户输入
            history: 对话历史

        Returns:
            最终结果，包含文本回复和工具执行结果
        """
        # 首先调用LLM
        result = await self.run(user_input, history)

        # 如果有工具调用，执行工具
        if result["has_tool_call"]:
            tool_results = []
            for tool_call in result["tool_calls"]:
                tool_result = await self.process_tool_call(tool_call)
                tool_results.append(tool_result)

            result["tool_results"] = tool_results

        return result

    def load_config_from_db(self):
        """
        从数据库加载配置

        加载：
        - 问候语
        - 拒绝话术
        - 法律范围定义
        """
        if not self._context or not self._context.db:
            return

        try:
            from app.models.config import ConfigRejectScript

            db = self._context.db

            # 加载拒绝话术
            reject_config = db.query(ConfigRejectScript).filter(
                ConfigRejectScript.is_active == True
            ).first()

            if reject_config and reject_config.content:
                self._rejection = reject_config.content

        except Exception as e:
            # 加载失败使用默认值
            pass
