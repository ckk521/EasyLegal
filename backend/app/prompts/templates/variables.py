"""
提示词变量模板 - 可被B端配置动态覆盖
"""

# 默认变量配置
DEFAULT_VARIABLES = {
    # 助手基本信息
    "assistant_name": "法律AI助手",
    "assistant_version": "1.0",

    # 回复风格
    "response_style": "专业且友好",
    "detail_level": "适中",  # 简洁/适中/详细

    # 法律范围（可被B端配置覆盖）
    "legal_scope_enabled": True,

    # 拒绝策略
    "rejection_enabled": True,
    "rejection_style": "polite",  # polite/direct/detailed

    # 安全设置
    "show_disclaimer": True,
    "disclaimer_frequency": "when_necessary",  # always/when_necessary/never
}

# 免责声明模板
DISCLAIMER_TEMPLATES = {
    "full": """
---
**免责声明**：以上内容仅供参考，不构成正式法律意见。具体法律问题请咨询专业律师获得针对性建议。
""",
    "brief": "（以上内容仅供参考，具体问题建议咨询专业律师）",
    "none": ""
}

# 问候语模板
GREETING_TEMPLATES = {
    "welcome": "您好！我是{assistant_name}，可以为您提供法律咨询服务。请问有什么可以帮助您的？",
    "returning": "欢迎回来！我是{assistant_name}，请问今天有什么法律问题需要咨询？",
    "after_rejection": "如果您有其他法律相关问题，请随时告诉我，我会尽力为您提供帮助。"
}
