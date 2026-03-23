"""
测试配置
"""
import pytest
import os
import sys
from pathlib import Path
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.staff import Staff
from app.utils.security import hash_password, create_token_for_user, create_token_for_staff


# 使用内存数据库进行测试
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator:
    """创建测试数据库会话"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

    # 测试结束后删除所有表
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> TestClient:
    """创建测试客户端"""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db: Session) -> User:
    """创建测试C端用户"""
    user = User(
        username="testuser",
        password=hash_password("test123456"),
        nickname="测试用户",
        status="active"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_staff(db: Session) -> Staff:
    """创建测试B端员工"""
    staff = Staff(
        username="operator",
        password=hash_password("operator123"),
        nickname="运营人员",
        role="operator",
        status="active",
        first_login=False
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


@pytest.fixture
def test_admin(db: Session) -> Staff:
    """创建测试B端管理员"""
    admin = Staff(
        username="admin",
        password=hash_password("admin123"),
        nickname="管理员",
        role="admin",
        status="active",
        first_login=False
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def user_token(client: TestClient, test_user: User) -> str:
    """获取C端用户token - 直接生成token"""
    return create_token_for_user(test_user)


@pytest.fixture
def staff_token(client: TestClient, test_staff: Staff) -> str:
    """获取B端员工token - 直接生成token"""
    return create_token_for_staff(test_staff)


@pytest.fixture
def admin_token(client: TestClient, test_admin: Staff) -> str:
    """获取B端管理员token - 直接生成token"""
    return create_token_for_staff(test_admin)
