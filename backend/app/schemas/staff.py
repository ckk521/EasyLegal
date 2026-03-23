"""
B端员工相关的Pydantic模型
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== 请求模型 ====================

class StaffLoginRequest(BaseModel):
    """B端员工登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class CreateStaffRequest(BaseModel):
    """创建员工请求"""
    username: str = Field(..., min_length=2, max_length=100, description="用户名")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    role: str = Field(default="operator", description="角色: admin/operator/viewer")


class UpdateStaffStatusRequest(BaseModel):
    """更新员工状态请求"""
    status: str = Field(..., description="状态: active/disabled")


class ChangeStaffPasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="原密码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")


# ==================== 响应模型 ====================

class StaffResponse(BaseModel):
    """B端员工信息响应"""
    id: int
    username: str
    nickname: Optional[str] = None
    role: str
    status: str
    first_login: bool = True
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StaffLoginResponse(BaseModel):
    """B端登录响应"""
    token: str
    token_type: str = "bearer"
    staff: StaffResponse
    first_login: bool = Field(..., description="是否首次登录（需修改密码）")


class StaffListResponse(BaseModel):
    """员工列表响应"""
    total: int
    items: list[StaffResponse]


class MessageResponse(BaseModel):
    """通用消息响应"""
    success: bool = True
    message: str
