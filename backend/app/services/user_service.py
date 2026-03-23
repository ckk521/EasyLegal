"""
C端用户业务服务
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.user import User
from app.utils.security import hash_password, verify_password


class UserService:
    """C端用户服务类"""

    @staticmethod
    def create_user(
        db: Session,
        username: str,
        password: str,
        nickname: Optional[str] = None
    ) -> User:
        """
        创建用户

        Args:
            db: 数据库会话
            username: 用户名
            password: 密码
            nickname: 昵称

        Returns:
            User对象
        """
        hashed_password = hash_password(password)
        user = User(
            username=username,
            password=hashed_password,
            nickname=nickname or username
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """
        验证用户登录

        Args:
            db: 数据库会话
            username: 用户名
            password: 密码

        Returns:
            验证成功返回User对象，失败返回None
        """
        user = UserService.get_user_by_username(db, username)
        if not user:
            return None
        if not verify_password(password, user.password):
            return None
        return user

    @staticmethod
    def update_last_login(db: Session, user: User, ip_address: Optional[str] = None) -> None:
        """更新最后登录时间"""
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = ip_address
        db.commit()

    @staticmethod
    def update_user_status(db: Session, user_id: int, status: str) -> Optional[User]:
        """更新用户状态"""
        user = UserService.get_user_by_id(db, user_id)
        if user:
            user.status = status
            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """删除用户（软删除）"""
        user = UserService.get_user_by_id(db, user_id)
        if user:
            user.status = "deleted"
            user.updated_at = datetime.utcnow()
            db.commit()
            return True
        return False

    @staticmethod
    def get_users(
        db: Session,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[User], int]:
        """
        获取用户列表

        Args:
            db: 数据库会话
            status: 状态过滤
            skip: 跳过数量
            limit: 返回数量

        Returns:
            (用户列表, 总数)
        """
        query = db.query(User).filter(User.status != "deleted")

        if status:
            query = query.filter(User.status == status)

        total = query.count()
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

        return users, total

    @staticmethod
    def change_password(db: Session, user: User, new_password: str) -> None:
        """修改密码"""
        user.password = hash_password(new_password)
        user.updated_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def update_nickname(db: Session, user: User, nickname: str) -> None:
        """更新昵称"""
        user.nickname = nickname
        user.updated_at = datetime.utcnow()
        db.commit()
