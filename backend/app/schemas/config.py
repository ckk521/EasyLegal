"""
配置相关的 Pydantic 模型
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# ==================== LLM 配置 ====================

class LLMConfigBase(BaseModel):
    """LLM配置基础模型"""
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(default="default", max_length=50, description="配置名称")
    api_key: str = Field(..., max_length=255, description="API Key")
    base_url: str = Field(..., max_length=255, description="Base URL")
    model_name: str = Field(..., max_length=100, description="模型名称")
    api_type: str = Field(default="openai-completions", max_length=50, description="API类型")
    is_active: bool = Field(default=True, description="是否启用")


class LLMConfigCreate(LLMConfigBase):
    """创建LLM配置"""
    pass


class LLMConfigUpdate(BaseModel):
    """更新LLM配置"""
    model_config = ConfigDict(protected_namespaces=())

    name: Optional[str] = Field(None, max_length=50)
    api_key: Optional[str] = Field(None, max_length=255)
    base_url: Optional[str] = Field(None, max_length=255)
    model_name: Optional[str] = Field(None, max_length=100)
    api_type: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class LLMConfigResponse(LLMConfigBase):
    """LLM配置响应"""
    id: int
    last_verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LLMVerifyRequest(BaseModel):
    """LLM配置验证请求"""
    model_config = ConfigDict(protected_namespaces=())

    api_key: str = Field(..., description="API Key")
    base_url: str = Field(..., description="Base URL")
    model_name: str = Field(..., description="模型名称")
    api_type: str = Field(default="openai-completions", description="API类型")


class LLMVerifyResponse(BaseModel):
    """LLM配置验证响应"""
    model_config = ConfigDict(protected_namespaces=())

    success: bool
    message: str
    model_info: Optional[dict] = None


# ==================== Embedding 配置 ====================

class EmbeddingConfigBase(BaseModel):
    """Embedding配置基础模型"""
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(default="default", max_length=50, description="配置名称")
    model_name: str = Field(default="m3e-base", max_length=100, description="模型名称")
    chunk_size: int = Field(default=512, ge=100, le=2000, description="Chunk大小")
    chunk_overlap: int = Field(default=50, ge=0, le=500, description="重叠大小")
    is_active: bool = Field(default=True, description="是否启用")


class EmbeddingConfigCreate(EmbeddingConfigBase):
    """创建Embedding配置"""
    pass


class EmbeddingConfigUpdate(BaseModel):
    """更新Embedding配置"""
    name: Optional[str] = Field(None, max_length=50)
    model_name: Optional[str] = Field(None, max_length=100)
    chunk_size: Optional[int] = Field(None, ge=100, le=2000)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=500)
    is_active: Optional[bool] = None


class EmbeddingConfigResponse(EmbeddingConfigBase):
    """Embedding配置响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 法律范围配置 ====================

class LegalScopeConfigBase(BaseModel):
    """法律范围配置基础模型"""
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(default="default", max_length=50, description="配置名称")
    scope_description: str = Field(..., description="法律范围描述")
    allowed_topics: Optional[str] = Field(None, description="允许的主题(JSON数组)")
    forbidden_topics: Optional[str] = Field(None, description="禁止的主题(JSON数组)")
    is_active: bool = Field(default=True, description="是否启用")


class LegalScopeConfigCreate(LegalScopeConfigBase):
    """创建法律范围配置"""
    pass


class LegalScopeConfigUpdate(BaseModel):
    """更新法律范围配置"""
    name: Optional[str] = Field(None, max_length=50)
    scope_description: Optional[str] = None
    allowed_topics: Optional[str] = None
    forbidden_topics: Optional[str] = None
    is_active: Optional[bool] = None


class LegalScopeConfigResponse(LegalScopeConfigBase):
    """法律范围配置响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 拒绝话术配置 ====================

class RejectScriptConfigBase(BaseModel):
    """拒绝话术配置基础模型"""
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(default="default", max_length=50, description="配置名称")
    rejection_message: str = Field(..., description="拒绝话术")
    redirect_template: Optional[str] = Field(None, description="引导话术模板")
    is_active: bool = Field(default=True, description="是否启用")


class RejectScriptConfigCreate(RejectScriptConfigBase):
    """创建拒绝话术配置"""
    pass


class RejectScriptConfigUpdate(BaseModel):
    """更新拒绝话术配置"""
    name: Optional[str] = Field(None, max_length=50)
    rejection_message: Optional[str] = None
    redirect_template: Optional[str] = None
    is_active: Optional[bool] = None


class RejectScriptConfigResponse(RejectScriptConfigBase):
    """拒绝话术配置响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 核心意图配置 ====================

class IntentConfigBase(BaseModel):
    """核心意图配置基础模型"""
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(..., max_length=100, description="意图名称")
    description: Optional[str] = Field(None, description="意图描述")
    trigger_words: Optional[str] = Field(None, description="触发词(JSON数组)")
    response_template: Optional[str] = Field(None, description="响应模板")
    priority: int = Field(default=0, ge=0, le=100, description="优先级")
    is_active: bool = Field(default=True, description="是否启用")


class IntentConfigCreate(IntentConfigBase):
    """创建核心意图配置"""
    pass


class IntentConfigUpdate(BaseModel):
    """更新核心意图配置"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    trigger_words: Optional[str] = None
    response_template: Optional[str] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None


class IntentConfigResponse(IntentConfigBase):
    """核心意图配置响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
