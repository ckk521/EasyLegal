"""
B端员工业务服务
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.staff import Staff
from app.utils.security import hash_password, verify_password


class StaffService:
    """B端员工服务类"""

    @staticmethod
    def create_staff(
        db: Session,
        username: str,
        password: str,
        nickname: Optional[str] = None,
        role: str = "operator"
    ) -> Staff:
        """
        创建员工

        Args:
            db: 数据库会话
            username: 用户名
            password: 密码
            nickname: 昵称
            role: 角色 (admin/operator/viewer)

        Returns:
            Staff对象
        """
        hashed_password = hash_password(password)
        staff = Staff(
            username=username,
            password=hashed_password,
            nickname=nickname or username,
            role=role
        )
        db.add(staff)
        db.commit()
        db.refresh(staff)
        return staff

    @staticmethod
    def get_staff_by_id(db: Session, staff_id: int) -> Optional[Staff]:
        """根据ID获取员工"""
        return db.query(Staff).filter(Staff.id == staff_id).first()

    @staticmethod
    def get_staff_by_username(db: Session, username: str) -> Optional[Staff]:
        """根据用户名获取员工"""
        return db.query(Staff).filter(Staff.username == username).first()

    @staticmethod
    def authenticate_staff(db: Session, username: str, password: str) -> Optional[Staff]:
        """
        验证员工登录

        Args:
            db: 数据库会话
            username: 用户名
            password: 密码

        Returns:
            验证成功返回Staff对象，失败返回None
        """
        staff = StaffService.get_staff_by_username(db, username)
        if not staff:
            return None
        if not verify_password(password, staff.password):
            return None
        return staff

    @staticmethod
    def update_last_login(db: Session, staff: Staff, ip_address: Optional[str] = None) -> None:
        """更新最后登录时间"""
        staff.last_login_at = datetime.utcnow()
        staff.last_login_ip = ip_address
        db.commit()

    @staticmethod
    def update_staff_status(db: Session, staff_id: int, status: str) -> Optional[Staff]:
        """更新员工状态"""
        staff = StaffService.get_staff_by_id(db, staff_id)
        if staff:
            staff.status = status
            staff.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(staff)
        return staff

    @staticmethod
    def delete_staff(db: Session, staff_id: int) -> bool:
        """删除员工（软删除）"""
        staff = StaffService.get_staff_by_id(db, staff_id)
        if staff:
            staff.status = "deleted"
            staff.updated_at = datetime.utcnow()
            db.commit()
            return True
        return False

    @staticmethod
    def get_staff_list(
        db: Session,
        role: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Staff], int]:
        """
        获取员工列表

        Args:
            db: 数据库会话
            role: 角色过滤
            status: 状态过滤
            skip: 跳过数量
            limit: 返回数量

        Returns:
            (员工列表, 总数)
        """
        query = db.query(Staff).filter(Staff.status != "deleted")

        if role:
            query = query.filter(Staff.role == role)
        if status:
            query = query.filter(Staff.status == status)

        total = query.count()
        staff_list = query.order_by(Staff.created_at.desc()).offset(skip).limit(limit).all()

        return staff_list, total

    @staticmethod
    def change_password(db: Session, staff: Staff, new_password: str) -> None:
        """修改密码"""
        staff.password = hash_password(new_password)
        staff.first_login = False
        staff.updated_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def update_nickname(db: Session, staff: Staff, nickname: str) -> None:
        """更新昵称"""
        staff.nickname = nickname
        staff.updated_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def create_admin_if_not_exists(db: Session) -> Staff:
        """
        创建默认admin账号（如果不存在）

        Returns:
            Staff对象
        """
        admin = StaffService.get_staff_by_username(db, "admin")
        if not admin:
            admin = StaffService.create_staff(
                db=db,
                username="admin",
                password="admin123",
                nickname="超级管理员",
                role="admin"
            )
            admin.first_login = False
            db.commit()
        return admin

    @staticmethod
    def has_permission(staff: Staff, required_roles: List[str] = None) -> bool:
        """
        检查员工是否有指定权限

        Args:
            staff: 员工对象
            required_roles: 需要的角色列表

        Returns:
            是否有权限
        """
        if required_roles is None:
            required_roles = ["admin"]
        return staff.role in required_roles
