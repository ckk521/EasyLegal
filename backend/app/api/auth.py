"""
认证API路由（C端用户）
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    UserResponse,
    ChangePasswordRequest,
    MessageResponse
)
from app.services.user_service import UserService
from app.utils.security import (
    create_token_for_user,
    get_current_user,
    verify_password
)
from app.utils.audit import audit_logger, AuditAction

router = APIRouter(prefix="/api/auth", tags=["C端认证"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    C端用户注册

    - 用户名可以是手机号、邮箱或自定义用户名
    - 密码长度6-50位
    """
    # 检查用户名是否已存在
    existing_user = UserService.get_user_by_username(db, request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    # 创建用户
    user = UserService.create_user(
        db=db,
        username=request.username,
        password=request.password,
        nickname=request.nickname
    )

    # 记录审计日志
    ip_address = None
    if http_request and http_request.client:
        ip_address = http_request.client.host
    audit_logger.log(
        action=AuditAction.USER_REGISTER,
        user_id=user.id,
        user_role="user",
        ip_address=ip_address
    )

    return RegisterResponse(user_id=user.id)


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    C端用户登录

    - 返回JWT token和用户信息
    - token有效期7天
    """
    # 验证用户
    user = UserService.authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查用户状态
    if user.status == "disabled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    if user.status == "deleted":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )

    # 更新最后登录时间
    ip_address = None
    if http_request and http_request.client:
        ip_address = http_request.client.host
    UserService.update_last_login(db, user, ip_address)

    # 生成token
    token = create_token_for_user(user)

    # 记录审计日志
    audit_logger.log(
        action=AuditAction.USER_LOGIN,
        user_id=user.id,
        user_role="user",
        ip_address=ip_address,
        user_agent=http_request.headers.get("user-agent") if http_request else None
    )

    return LoginResponse(
        token=token,
        user=UserResponse.model_validate(user)
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    current_user: User = Depends(get_current_user),
    http_request: Request = None
):
    """
    C端用户登出

    - 客户端应删除本地存储的token
    """
    # 记录审计日志
    ip_address = None
    if http_request and http_request.client:
        ip_address = http_request.client.host
    audit_logger.log(
        action=AuditAction.USER_LOGOUT,
        user_id=current_user.id,
        user_role="user",
        ip_address=ip_address
    )

    return MessageResponse(message="登出成功")


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    获取当前C端用户信息
    """
    return UserResponse.model_validate(current_user)


@router.put("/password", response_model=MessageResponse)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    C端用户修改密码

    - 需要验证原密码
    """
    # 验证原密码
    if not verify_password(request.old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误"
        )

    # 修改密码
    UserService.change_password(db, current_user, request.new_password)

    return MessageResponse(message="密码修改成功")


@router.put("/nickname", response_model=UserResponse)
def update_nickname(
    nickname: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    C端用户更新昵称
    """
    UserService.update_nickname(db, current_user, nickname)
    return UserResponse.model_validate(current_user)
