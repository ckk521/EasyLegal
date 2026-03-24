"""
聊天记录模型

用于存储用户与智能体的对话历史，确保对话能够衔接。
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class ChatSession(Base):
    """对话会话表"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=True)  # 会话标题，可从首条消息生成
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)  # 关联的合同ID
    status = Column(String(20), default="active")  # active=进行中, archived=已归档
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", backref="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    contract = relationship("Contract", backref="chat_session")


class ChatMessage(Base):
    """对话消息表"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user 或 assistant
    content = Column(Text, nullable=False)  # 消息内容
    meta_data = Column(JSON, nullable=True)  # 元数据（工具调用、表单等）
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    session = relationship("ChatSession", back_populates="messages")
