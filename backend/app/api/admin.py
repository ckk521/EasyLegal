"""
B端管理API路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.staff import Staff
from app.schemas.user import (
    UserResponse,
    UserListResponse,
    UpdateUserStatusRequest,
    MessageResponse
)
from app.schemas.staff import (
    StaffResponse,
    StaffListResponse,
    CreateStaffRequest,
    UpdateStaffStatusRequest
)
from app.services.user_service import UserService
from app.services.staff_service import StaffService
from app.utils.security import get_current_admin
from app.utils.audit import audit_logger, AuditAction

router = APIRouter(prefix="/api/admin", tags=["B端管理"])


# ==================== C端用户管理 ====================

@router.get("/users", response_model=UserListResponse)
def get_users(
    status: Optional[str] = Query(None, description="状态过滤: active/disabled"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取C端用户列表

    - 需要管理员权限
    - 支持按状态过滤
    """
    users, total = UserService.get_users(
        db=db,
        status=status,
        skip=skip,
        limit=limit
    )

    return UserListResponse(
        total=total,
        items=[UserResponse.model_validate(u) for u in users]
    )


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取C端用户详情

    - 需要管理员权限
    """
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return UserResponse.model_validate(user)


@router.put("/users/{user_id}/status", response_model=MessageResponse)
def update_user_status(
    user_id: int,
    request: UpdateUserStatusRequest,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    更新C端用户状态

    - 需要管理员权限
    - 可启用或禁用用户
    """
    # 检查状态值
    if request.status not in ["active", "disabled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="状态值无效，只能是 active 或 disabled"
        )

    user = UserService.update_user_status(db, user_id, request.status)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 记录审计日志
    ip_address = None
    if http_request and http_request.client:
        ip_address = http_request.client.host
    audit_logger.log(
        action=AuditAction.USER_STATUS_CHANGE,
        user_id=current_admin.id,
        user_role=current_admin.role,
        resource_type="user",
        resource_id=user_id,
        detail={"new_status": request.status},
        ip_address=ip_address
    )

    return MessageResponse(message=f"用户状态已更新为 {request.status}")


@router.delete("/users/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: int,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    删除C端用户（软删除）

    - 需要管理员权限
    """
    success = UserService.delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 记录审计日志
    ip_address = None
    if http_request and http_request.client:
        ip_address = http_request.client.host
    audit_logger.log(
        action=AuditAction.USER_DELETE,
        user_id=current_admin.id,
        user_role=current_admin.role,
        resource_type="user",
        resource_id=user_id,
        ip_address=ip_address
    )

    return MessageResponse(message="用户已删除")


# ==================== B端员工管理 ====================

@router.get("/staff", response_model=StaffListResponse)
def get_staff_list(
    role: Optional[str] = Query(None, description="角色过滤: admin/operator/viewer"),
    status: Optional[str] = Query(None, description="状态过滤: active/disabled"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取B端员工列表

    - 需要管理员权限
    """
    staff_list, total = StaffService.get_staff_list(
        db=db,
        role=role,
        status=status,
        skip=skip,
        limit=limit
    )

    return StaffListResponse(
        total=total,
        items=[StaffResponse.model_validate(s) for s in staff_list]
    )


@router.post("/staff", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
def create_staff(
    request: CreateStaffRequest,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    创建B端员工

    - 需要管理员权限
    """
    # 检查用户名是否已存在
    existing = StaffService.get_staff_by_username(db, request.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    staff = StaffService.create_staff(
        db=db,
        username=request.username,
        password=request.password,
        nickname=request.nickname,
        role=request.role
    )

    return StaffResponse.model_validate(staff)


@router.get("/staff/{staff_id}", response_model=StaffResponse)
def get_staff(
    staff_id: int,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取B端员工详情

    - 需要管理员权限
    """
    staff = StaffService.get_staff_by_id(db, staff_id)
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="员工不存在"
        )

    return StaffResponse.model_validate(staff)


@router.put("/staff/{staff_id}/status", response_model=MessageResponse)
def update_staff_status(
    staff_id: int,
    request: UpdateStaffStatusRequest,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    更新B端员工状态

    - 需要管理员权限
    - 不能修改自己的状态
    """
    # 不能修改自己
    if staff_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能修改自己的状态"
        )

    # 检查状态值
    if request.status not in ["active", "disabled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="状态值无效，只能是 active 或 disabled"
        )

    staff = StaffService.update_staff_status(db, staff_id, request.status)
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="员工不存在"
        )

    # 记录审计日志
    ip_address = None
    if http_request and http_request.client:
        ip_address = http_request.client.host
    audit_logger.log(
        action=AuditAction.USER_STATUS_CHANGE,
        user_id=current_admin.id,
        user_role=current_admin.role,
        resource_type="staff",
        resource_id=staff_id,
        detail={"new_status": request.status},
        ip_address=ip_address
    )

    return MessageResponse(message=f"员工状态已更新为 {request.status}")


@router.delete("/staff/{staff_id}", response_model=MessageResponse)
def delete_staff(
    staff_id: int,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    删除B端员工（软删除）

    - 需要管理员权限
    - 不能删除自己
    """
    # 不能删除自己
    if staff_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己"
        )

    success = StaffService.delete_staff(db, staff_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="员工不存在"
        )

    # 记录审计日志
    ip_address = None
    if http_request and http_request.client:
        ip_address = http_request.client.host
    audit_logger.log(
        action=AuditAction.USER_DELETE,
        user_id=current_admin.id,
        user_role=current_admin.role,
        resource_type="staff",
        resource_id=staff_id,
        ip_address=ip_address
    )

    return MessageResponse(message="员工已删除")


# ==================== 仪表盘统计 ====================

@router.get("/dashboard/stats")
def get_dashboard_stats(
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取仪表盘统计数据

    - 需要管理员权限
    """
    # 统计C端用户数量
    total_users = db.query(User).filter(User.status != "deleted").count()
    active_users = db.query(User).filter(User.status == "active").count()

    # 统计B端员工数量
    total_staff = db.query(Staff).filter(Staff.status != "deleted").count()
    admin_count = db.query(Staff).filter(
        Staff.status == "active",
        Staff.role == "admin"
    ).count()

    return {
        "users": {
            "total": total_users,
            "active": active_users
        },
        "staff": {
            "total": total_staff,
            "admin_count": admin_count
        }
    }
