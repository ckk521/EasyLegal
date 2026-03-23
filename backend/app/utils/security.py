"""
安全工具模块：JWT生成/验证、密码加密
"""
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.staff import Staff

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer认证
security = HTTPBearer()


def hash_password(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建JWT访问令牌

    Args:
        data: 要编码的数据（通常包含user_id和type）
        expires_delta: 过期时间增量

    Returns:
        JWT令牌字符串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码JWT令牌

    Args:
        token: JWT令牌字符串

    Returns:
        解码后的数据字典，解码失败返回None
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前登录的C端用户（依赖注入）

    Raises:
        HTTPException: Token无效或用户不存在

    Returns:
        User对象
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    user_id_str = payload.get("sub")
    token_type = payload.get("type", "user")

    if user_id_str is None:
        raise credentials_exception

    # 确保是C端用户的token
    if token_type != "user":
        raise credentials_exception

    try:
        user_id: int = int(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    return user


def get_current_staff(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Staff:
    """
    获取当前登录的B端员工（依赖注入）

    Raises:
        HTTPException: Token无效或员工不存在

    Returns:
        Staff对象
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    staff_id_str = payload.get("sub")
    token_type = payload.get("type", "staff")

    if staff_id_str is None:
        raise credentials_exception

    # 确保是B端员工的token
    if token_type != "staff":
        raise credentials_exception

    try:
        staff_id: int = int(staff_id_str)
    except (ValueError, TypeError):
        raise credentials_exception

    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if staff is None:
        raise credentials_exception

    if staff.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )

    return staff


def get_current_admin(
    current_staff: Staff = Depends(get_current_staff)
) -> Staff:
    """
    获取当前登录的管理员员工（依赖注入）

    Raises:
        HTTPException: 非管理员

    Returns:
        Staff对象
    """
    if current_staff.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限"
        )
    return current_staff


def create_token_for_user(user: User) -> str:
    """
    为C端用户创建JWT令牌

    Args:
        user: User对象

    Returns:
        JWT令牌字符串
    """
    token_data = {
        "sub": str(user.id),  # JWT sub字段必须是字符串
        "type": "user",
        "username": user.username
    }
    return create_access_token(token_data)


def create_token_for_staff(staff: Staff) -> str:
    """
    为B端员工创建JWT令牌

    Args:
        staff: Staff对象

    Returns:
        JWT令牌字符串
    """
    token_data = {
        "sub": str(staff.id),
        "type": "staff",
        "role": staff.role,
        "username": staff.username
    }
    return create_access_token(token_data)
