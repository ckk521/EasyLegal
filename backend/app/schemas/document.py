"""
文档相关的 Pydantic 模型
"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict


# ==================== 文档 ====================

class DocumentBase(BaseModel):
    """文档基础模型"""
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(..., max_length=255, description="文档名称")
    doc_type: str = Field(default="other", description="文档类别")
    description: Optional[str] = Field(None, description="描述")


class DocumentCreate(DocumentBase):
    """创建文档"""
    pass


class DocumentResponse(DocumentBase):
    """文档响应"""
    id: int
    file_path: str
    file_type: str
    content: Optional[str] = None
    chunk_count: int = 0
    is_indexed: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    total: int
    items: List[DocumentResponse]


# ==================== 合同模板 ====================

class TemplateBase(BaseModel):
    """模板基础模型"""
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(..., max_length=255, description="模板名称")
    contract_type: str = Field(..., max_length=100, description="合同类型")
    description: Optional[str] = Field(None, description="描述")


class TemplateCreate(TemplateBase):
    """创建模板"""
    pass


class TemplateUpdate(BaseModel):
    """更新模板"""
    model_config = ConfigDict(protected_namespaces=())

    name: Optional[str] = Field(None, max_length=255)
    contract_type: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class TemplateResponse(TemplateBase):
    """模板响应"""
    id: int
    file_path: str
    file_type: str
    content: Optional[str] = None
    variables: Optional[str] = None
    field_definition_id: Optional[int] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 字段定义 ====================

class FieldDefinitionBase(BaseModel):
    """字段定义基础模型"""
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(..., max_length=100, description="定义名称")
    contract_type: str = Field(..., max_length=100, description="合同类型")
    fields: str = Field(..., description="字段定义(JSON)")


class FieldDefinitionCreate(FieldDefinitionBase):
    """创建字段定义"""
    pass


class FieldDefinitionUpdate(BaseModel):
    """更新字段定义"""
    model_config = ConfigDict(protected_namespaces=())

    name: Optional[str] = Field(None, max_length=100)
    contract_type: Optional[str] = Field(None, max_length=100)
    fields: Optional[str] = None
    is_active: Optional[bool] = None


class FieldDefinitionResponse(FieldDefinitionBase):
    """字段定义响应"""
    id: int
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 合同字段 ====================

class ContractField(BaseModel):
    """合同字段"""
    name: str = Field(..., description="字段名称")
    label: str = Field(..., description="显示名称")
    type: str = Field(default="text", description="字段类型(text/number/date/select/textarea)")
    required: bool = Field(default=True, description="是否必填")
    default: Optional[str] = Field(None, description="默认值")
    options: Optional[List[str]] = Field(None, description="选项(select类型)")
    placeholder: Optional[str] = Field(None, description="占位提示")
    description: Optional[str] = Field(None, description="字段说明")
    order: int = Field(default=0, description="排序")


class ContractFieldValues(BaseModel):
    """合同字段值"""
    contract_type: str
    fields: dict[str, Any]
