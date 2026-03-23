"""
文档相关数据库模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Enum
from app.database import Base
import enum


class DocumentType(str, enum.Enum):
    """文档类型"""
    TEMPLATE = "template"      # 合同模板
    CASE = "case"              # 案例文档
    RULE = "rule"              # 审核规则
    INTENT = "intent"          # 核心意图文档
    OTHER = "other"            # 其他


class Document(Base):
    """文档表"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="文档名称")
    file_path = Column(String(500), nullable=False, comment="文件存储路径")
    file_type = Column(String(50), nullable=False, comment="文件类型(pdf/docx/md/txt)")
    doc_type = Column(String(20), nullable=False, default=DocumentType.OTHER, comment="文档类别")
    content = Column(Text, nullable=True, comment="解析后的文本内容")
    chunk_count = Column(Integer, default=0, comment="向量块数量")
    is_indexed = Column(Boolean, default=False, comment="是否已索引到向量库")
    description = Column(Text, nullable=True, comment="描述")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Template(Base):
    """合同模板表"""
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="模板名称")
    contract_type = Column(String(100), nullable=False, comment="合同类型")
    file_path = Column(String(500), nullable=False, comment="文件存储路径")
    file_type = Column(String(50), nullable=False, comment="文件类型")
    content = Column(Text, nullable=True, comment="模板内容")
    variables = Column(Text, nullable=True, comment="模板变量(JSON)")
    field_definition_id = Column(Integer, nullable=True, comment="关联的字段定义ID")
    is_active = Column(Boolean, default=True, comment="是否启用")
    description = Column(Text, nullable=True, comment="描述")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class FieldDefinition(Base):
    """合同字段定义表"""
    __tablename__ = "field_definitions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="定义名称")
    contract_type = Column(String(100), nullable=False, comment="合同类型")
    fields = Column(Text, nullable=False, comment="字段定义(JSON)")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Contract(Base):
    """合同记录表"""
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    contract_no = Column(String(50), unique=True, nullable=False, comment="合同编号")
    user_id = Column(Integer, nullable=False, index=True, comment="用户ID")
    template_id = Column(Integer, nullable=True, comment="模板ID")
    contract_type = Column(String(100), nullable=False, comment="合同类型")
    title = Column(String(255), nullable=True, comment="合同标题")
    status = Column(String(20), default="draft", comment="状态(draft/pending/completed/cancelled)")
    field_values = Column(Text, nullable=True, comment="字段值(JSON)")
    content = Column(Text, nullable=True, comment="合同内容")
    file_path = Column(String(500), nullable=True, comment="导出文件路径")
    session_id = Column(Integer, nullable=True, comment="关联的会话ID")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
