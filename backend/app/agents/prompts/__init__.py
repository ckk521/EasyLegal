"""
智能体提示词模块

提示词设计原则：
1. 清晰定义智能体的角色和能力
2. 说明可用的工具及其使用时机
3. 定义工作流程和决策规则
4. 提供示例帮助理解
"""

from app.agents.prompts.contract_prompts import CONTRACT_AGENT_SYSTEM_PROMPT

__all__ = ["CONTRACT_AGENT_SYSTEM_PROMPT"]
