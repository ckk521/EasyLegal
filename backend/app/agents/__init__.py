"""
智能体模块

架构说明：
- agents/ 是独立的智能体模块
- tools/ 定义智能体可调用的工具
- prompts/ 定义智能体的提示词
- 每个 Agent 是独立的个体，有自己的工具和提示词配置
"""

from app.agents.base import BaseAgent
from app.agents.contract_agent import ContractAgent

__all__ = ["BaseAgent", "ContractAgent"]
