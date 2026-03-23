"""
B端员工模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database import Base


class Staff(Base):
    """B端员工表"""
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    nickname = Column(String(50))
    role = Column(String(20), nullable=False, default="operator")  # admin/operator/viewer
    status = Column(String(20), nullable=False, default="active")  # active/disabled
    first_login = Column(Boolean, default=True)  # 是否首次登录（需修改密码）
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
