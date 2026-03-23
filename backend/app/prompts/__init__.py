"""
提示词加载器 - 统一管理所有提示词

使用方式：
    from app.prompts import PromptLoader

    # 获取完整的系统提示词
    system_prompt = PromptLoader.get_system_prompt()

    # 获取拒绝话术
    rejection = PromptLoader.get_rejection_template("general")
"""

from typing import Optional, Dict, Any
from string import Template

# 导入各类提示词
from app.prompts.system.base import (
    LEGAL_ASSISTANT_BASE,
    LEGAL_SCOPE_DEFAULT
)
from app.prompts.system.constraints import (
    REJECTION_GUIDELINES,
    REJECTION_TEMPLATES as CONSTRAINT_REJECTION_TEMPLATES,
    SAFETY_CONSTRAINTS
)
from app.prompts.intents.recognition import (
    INTENT_RECOGNITION_SYSTEM,
    INTENT_RECOGNITION_USER_TEMPLATE
)
from app.prompts.intents.contract import (
    CONTRACT_GENERATION_SYSTEM,
    CONTRACT_FIELD_COLLECTION_TEMPLATE,
    LEASE_CONTRACT_PROMPT,
    LABOR_CONTRACT_PROMPT
)
from app.prompts.rejection.templates import (
    REJECTION_TEMPLATES,
    REDIRECT_TEMPLATES,
    SERVICE_RECOMMENDATIONS
)
from app.prompts.templates.variables import (
    DEFAULT_VARIABLES,
    DISCLAIMER_TEMPLATES,
    GREETING_TEMPLATES
)


class PromptLoader:
    """提示词加载器"""

    _instance = None
    _variables: Dict[str, Any] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._variables = DEFAULT_VARIABLES.copy()
        return cls._instance

    @classmethod
    def set_variables(cls, variables: Dict[str, Any]) -> None:
        """设置变量（可被B端配置覆盖）"""
        instance = cls()
        instance._variables.update(variables)

    @classmethod
    def get_variables(cls) -> Dict[str, Any]:
        """获取当前变量配置"""
        instance = cls()
        return instance._variables.copy()

    @classmethod
    def get_system_prompt(
        cls,
        include_legal_scope: bool = True,
        include_safety: bool = True,
        include_rejection: bool = True
    ) -> str:
        """
        获取完整的系统提示词

        Args:
            include_legal_scope: 是否包含法律范围界定
            include_safety: 是否包含安全约束
            include_rejection: 是否包含拒绝策略

        Returns:
            完整的系统提示词字符串
        """
        parts = [LEGAL_ASSISTANT_BASE]

        if include_legal_scope:
            parts.append("\n\n" + LEGAL_SCOPE_DEFAULT)

        if include_rejection:
            parts.append("\n\n" + REJECTION_GUIDELINES)

        if include_safety:
            parts.append("\n\n" + SAFETY_CONSTRAINTS)

        return "\n".join(parts)

    @classmethod
    def get_rejection_template(cls, template_type: str = "general") -> str:
        """
        获取拒绝话术模板

        Args:
            template_type: 模板类型 (general, small_talk, medical, investment, technical, daily_info, entertainment)

        Returns:
            拒绝话术字符串
        """
        return REJECTION_TEMPLATES.get(template_type, REJECTION_TEMPLATES["general"])

    @classmethod
    def get_redirect_template(cls, style: str = "medium") -> str:
        """
        获取引导回复模板

        Args:
            style: 风格 (soft, medium, hard)

        Returns:
            引导回复字符串
        """
        return REDIRECT_TEMPLATES.get(style, REDIRECT_TEMPLATES["medium"])

    @classmethod
    def get_intent_recognition_prompt(cls, user_input: str) -> str:
        """
        获取意图识别提示词

        Args:
            user_input: 用户输入

        Returns:
            意图识别提示词
        """
        return INTENT_RECOGNITION_SYSTEM, INTENT_RECOGNITION_USER_TEMPLATE.format(user_input=user_input)

    @classmethod
    def get_contract_generation_prompt(cls, contract_type: str = "general") -> str:
        """
        获取合同生成提示词

        Args:
            contract_type: 合同类型 (lease, labor, general)

        Returns:
            合同生成提示词
        """
        base_prompt = CONTRACT_GENERATION_SYSTEM

        if contract_type == "lease":
            return base_prompt + "\n\n" + LEASE_CONTRACT_PROMPT
        elif contract_type == "labor":
            return base_prompt + "\n\n" + LABOR_CONTRACT_PROMPT

        return base_prompt

    @classmethod
    def get_greeting(cls, greeting_type: str = "welcome") -> str:
        """
        获取问候语

        Args:
            greeting_type: 问候语类型 (welcome, returning, after_rejection)

        Returns:
            格式化后的问候语
        """
        template = GREETING_TEMPLATES.get(greeting_type, GREETING_TEMPLATES["welcome"])
        return template.format(**cls()._variables)

    @classmethod
    def get_disclaimer(cls, style: str = "brief") -> str:
        """
        获取免责声明

        Args:
            style: 风格 (full, brief, none)

        Returns:
            免责声明字符串
        """
        return DISCLAIMER_TEMPLATES.get(style, DISCLAIMER_TEMPLATES["brief"])

    @classmethod
    def get_service_recommendations(cls) -> str:
        """获取服务推荐列表"""
        return SERVICE_RECOMMENDATIONS


# 便捷导出
__all__ = [
    'PromptLoader',
    'LEGAL_ASSISTANT_BASE',
    'LEGAL_SCOPE_DEFAULT',
    'REJECTION_GUIDELINES',
    'REJECTION_TEMPLATES',
    'SAFETY_CONSTRAINTS',
    'INTENT_RECOGNITION_SYSTEM',
    'CONTRACT_GENERATION_SYSTEM',
    'DEFAULT_VARIABLES',
]
