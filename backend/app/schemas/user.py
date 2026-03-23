"""
用户相关的Pydantic模型
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== 请求模型 ====================

class RegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=2, max_length=100, description="用户名/手机号/邮箱")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")


class LoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UpdateUserStatusRequest(BaseModel):
    """更新用户状态请求"""
    status: str = Field(..., description="状态: active/disabled")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="原密码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")


# ==================== 响应模型 ====================

class UserResponse(BaseModel):
    """C端用户信息响应"""
    id: int
    username: str
    nickname: Optional[str] = None
    status: str
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RegisterResponse(BaseModel):
    """注册响应"""
    user_id: int
    message: str = "注册成功"


class LoginResponse(BaseModel):
    """登录响应"""
    token: str
    token_type: str = "bearer"
    user: UserResponse


class UserListResponse(BaseModel):
    """用户列表响应"""
    total: int
    items: list[UserResponse]


class MessageResponse(BaseModel):
    """通用消息响应"""
    success: bool = True
    message: str
