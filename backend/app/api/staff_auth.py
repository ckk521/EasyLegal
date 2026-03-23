"""
B端员工认证API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.staff import Staff
from app.schemas.staff import (
    StaffLoginRequest,
    StaffLoginResponse,
    StaffResponse,
    ChangeStaffPasswordRequest,
    MessageResponse
)
from app.schemas.user import UserResponse
from app.services.staff_service import StaffService
from app.utils.security import (
    create_token_for_staff,
    get_current_staff,
    verify_password
)
from app.utils.audit import audit_logger, AuditAction

router = APIRouter(prefix="/api/staff/auth", tags=["B端认证"])


@router.post("/login", response_model=StaffLoginResponse)
def login(
    request: StaffLoginRequest,
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    B端员工登录

    - 返回JWT token和员工信息
    - token有效期7天
    - 首次登录需要修改密码
    """
    # 验证员工
    staff = StaffService.authenticate_staff(db, request.username, request.password)
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查员工状态
    if staff.status == "disabled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )

    # 更新最后登录时间
    ip_address = None
    if http_request and http_request.client:
        ip_address = http_request.client.host
    StaffService.update_last_login(db, staff, ip_address)

    # 生成token
    token = create_token_for_staff(staff)

    # 记录审计日志
    audit_logger.log(
        action=AuditAction.USER_LOGIN,
        user_id=staff.id,
        user_role=staff.role,
        ip_address=ip_address,
        user_agent=http_request.headers.get("user-agent") if http_request else None
    )

    return StaffLoginResponse(
        token=token,
        staff=StaffResponse.model_validate(staff),
        first_login=staff.first_login
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    current_staff: Staff = Depends(get_current_staff),
    http_request: Request = None
):
    """
    B端员工登出

    - 客户端应删除本地存储的token
    """
    # 记录审计日志
    ip_address = None
    if http_request and http_request.client:
        ip_address = http_request.client.host
    audit_logger.log(
        action=AuditAction.USER_LOGOUT,
        user_id=current_staff.id,
        user_role=current_staff.role,
        ip_address=ip_address
    )

    return MessageResponse(message="登出成功")


@router.get("/me", response_model=StaffResponse)
def get_current_staff_info(current_staff: Staff = Depends(get_current_staff)):
    """
    获取当前B端员工信息
    """
    return StaffResponse.model_validate(current_staff)


@router.put("/password", response_model=MessageResponse)
def change_password(
    request: ChangeStaffPasswordRequest,
    current_staff: Staff = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    """
    B端员工修改密码

    - 需要验证原密码
    - 首次登录需强制修改密码
    """
    # 验证原密码
    if not verify_password(request.old_password, current_staff.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误"
        )

    # 修改密码
    StaffService.change_password(db, current_staff, request.new_password)

    return MessageResponse(message="密码修改成功")


@router.put("/nickname", response_model=StaffResponse)
def update_nickname(
    nickname: str,
    current_staff: Staff = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    """
    B端员工更新昵称
    """
    StaffService.update_nickname(db, current_staff, nickname)
    return StaffResponse.model_validate(current_staff)
