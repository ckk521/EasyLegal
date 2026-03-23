"""系统提示词模块"""
from app.prompts.system.base import LEGAL_ASSISTANT_BASE, LEGAL_SCOPE_DEFAULT
from app.prompts.system.constraints import REJECTION_GUIDELINES, SAFETY_CONSTRAINTS

__all__ = [
    'LEGAL_ASSISTANT_BASE',
    'LEGAL_SCOPE_DEFAULT',
    'REJECTION_GUIDELINES',
    'SAFETY_CONSTRAINTS',
]
