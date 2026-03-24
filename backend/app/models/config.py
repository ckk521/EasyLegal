"""
配置相关数据库模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from app.database import Base


class LLMConfig(Base):
    """大模型配置表"""
    __tablename__ = "config_llm"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False, default="default", comment="配置名称")
    api_key = Column(String(255), nullable=False, comment="API Key")
    base_url = Column(String(255), nullable=False, comment="Base URL")
    model_name = Column(String(100), nullable=False, comment="模型名称")
    api_type = Column(String(50), nullable=False, default="openai-completions", comment="API类型")
    is_active = Column(Boolean, default=True, comment="是否启用")
    last_verified_at = Column(DateTime, nullable=True, comment="最后验证时间")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class EmbeddingConfig(Base):
    """Embedding配置表"""
    __tablename__ = "config_embedding"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False, default="default", comment="配置名称")
    model_name = Column(String(100), nullable=False, default="m3e-base", comment="模型名称")
    chunk_size = Column(Integer, nullable=False, default=512, comment="Chunk大小")
    chunk_overlap = Column(Integer, nullable=False, default=50, comment="重叠大小")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class LegalScopeConfig(Base):
    """法律范围配置表"""
    __tablename__ = "config_legal_scope"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False, default="default", comment="配置名称")
    scope_description = Column(Text, nullable=False, comment="法律范围描述")
    allowed_topics = Column(Text, nullable=True, comment="允许的主题(JSON数组)")
    forbidden_topics = Column(Text, nullable=True, comment="禁止的主题(JSON数组)")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class RejectScriptConfig(Base):
    """拒绝话术配置表"""
    __tablename__ = "config_reject_script"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False, default="default", comment="配置名称")
    rejection_message = Column(Text, nullable=False, comment="拒绝话术")
    redirect_template = Column(Text, nullable=True, comment="引导话术模板")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class IntentConfig(Base):
    """核心意图配置表"""
    __tablename__ = "config_intent"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="意图名称")
    description = Column(Text, nullable=True, comment="意图描述")
    trigger_words = Column(Text, nullable=True, comment="触发词(JSON数组)")
    response_template = Column(Text, nullable=True, comment="响应模板")
    priority = Column(Integer, default=0, comment="优先级(数字越大优先级越高)")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
