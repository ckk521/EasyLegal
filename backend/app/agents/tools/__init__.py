"""
智能体工具模块

工具定义规范：
1. 每个工具对应一个具体的业务操作
2. 工具描述要清晰，让LLM知道何时调用
3. 工具执行后返回结构化的结果

工具调用流程：
Agent -> Tool -> Service/API -> Database
"""

from app.agents.tools.contract_tools import (
    create_contract_tools,
    get_contract_form,
    ask_contract_type,
    get_template_list,
    save_contract_draft,
    TOOL_EXECUTORS,
)

__all__ = [
    "create_contract_tools",
    "get_contract_form",
    "ask_contract_type",
    "get_template_list",
    "save_contract_draft",
    "TOOL_EXECUTORS",
]
