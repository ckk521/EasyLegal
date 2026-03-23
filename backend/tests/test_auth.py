"""
认证接口测试用例
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.staff import Staff


# ==================== C端用户测试 ====================

class TestUserRegister:
    """C端用户注册测试"""

    def test_register_success(self, client: TestClient):
        """测试注册成功"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "password": "password123",
                "nickname": "新用户"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] is not None
        assert data["message"] == "注册成功"

    def test_register_duplicate_username(self, client: TestClient, test_user: User):
        """测试注册重复用户名"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "password": "password123"
            }
        )
        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]

    def test_register_short_password(self, client: TestClient):
        """测试密码过短"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "password": "123"  # 少于6位
            }
        )
        assert response.status_code == 422  # 验证错误


class TestUserLogin:
    """C端用户登录测试"""

    def test_login_success(self, client: TestClient, test_user: User):
        """测试登录成功"""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "test123456"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["token"] is not None
        assert data["user"]["username"] == "testuser"

    def test_login_wrong_password(self, client: TestClient, test_user: User):
        """测试密码错误"""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """测试用户不存在"""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "nonexistent",
                "password": "password123"
            }
        )
        assert response.status_code == 401

    def test_login_disabled_user(self, client: TestClient, db: Session, test_user: User):
        """测试禁用用户登录"""
        test_user.status = "disabled"
        db.commit()

        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "test123456"
            }
        )
        assert response.status_code == 403
        assert "禁用" in response.json()["detail"]


class TestUserGetCurrentUser:
    """C端用户获取当前用户测试"""

    def test_get_current_user_success(self, client: TestClient, user_token: str):
        """测试获取当前用户"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"

    def test_get_current_user_no_token(self, client: TestClient):
        """测试无token"""
        response = client.get("/api/auth/me")
        assert response.status_code == 403

    def test_get_current_user_invalid_token(self, client: TestClient):
        """测试无效token"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401


class TestUserLogout:
    """C端用户登出测试"""

    def test_logout_success(self, client: TestClient, user_token: str):
        """测试登出"""
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestUserPasswordAndNickname:
    """C端用户密码和昵称修改测试"""

    def test_change_password_success(self, client: TestClient, user_token: str, test_user: User, db: Session):
        """测试修改密码成功"""
        response = client.put(
            "/api/auth/password",
            json={
                "old_password": "test123456",
                "new_password": "newpassword123"
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        assert "成功" in response.json()["message"]

        # 验证新密码可以登录
        login_response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "newpassword123"}
        )
        assert login_response.status_code == 200

    def test_change_password_wrong_old(self, client: TestClient, user_token: str):
        """测试原密码错误"""
        response = client.put(
            "/api/auth/password",
            json={
                "old_password": "wrongpassword",
                "new_password": "newpassword123"
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 400
        assert "错误" in response.json()["detail"]

    def test_update_nickname_success(self, client: TestClient, user_token: str):
        """测试更新昵称"""
        response = client.put(
            "/api/auth/nickname?nickname=新昵称",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        assert response.json()["nickname"] == "新昵称"


# ==================== B端员工测试 ====================

class TestStaffLogin:
    """B端员工登录测试"""

    def test_staff_login_success(self, client: TestClient, test_admin: Staff):
        """测试B端管理员登录成功"""
        response = client.post(
            "/api/staff/auth/login",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["token"] is not None
        assert data["staff"]["username"] == "admin"
        assert data["staff"]["role"] == "admin"

    def test_staff_login_wrong_password(self, client: TestClient, test_admin: Staff):
        """测试B端员工密码错误"""
        response = client.post(
            "/api/staff/auth/login",
            json={
                "username": "admin",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401

    def test_staff_login_disabled(self, client: TestClient, db: Session, test_admin: Staff):
        """测试B端员工被禁用"""
        test_admin.status = "disabled"
        db.commit()

        response = client.post(
            "/api/staff/auth/login",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        assert response.status_code == 403


class TestStaffGetCurrentUser:
    """B端员工获取当前信息测试"""

    def test_get_current_staff_success(self, client: TestClient, admin_token: str):
        """测试获取当前B端员工信息"""
        response = client.get(
            "/api/staff/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"


class TestStaffLogout:
    """B端员工登出测试"""

    def test_staff_logout_success(self, client: TestClient, admin_token: str):
        """测试B端员工登出"""
        response = client.post(
            "/api/staff/auth/logout",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True


# ==================== 管理员用户管理测试 ====================

class TestAdminUserManagement:
    """管理员用户管理测试"""

    def test_get_users_list(self, client: TestClient, admin_token: str, test_user: User):
        """测试获取用户列表"""
        response = client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_get_users_filter_by_status(self, client: TestClient, admin_token: str, test_user: User):
        """测试按状态筛选用户"""
        response = client.get(
            "/api/admin/users?status=active",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "active"

    def test_update_user_status(self, client: TestClient, admin_token: str, test_user: User):
        """测试更新用户状态"""
        response = client.put(
            f"/api/admin/users/{test_user.id}/status",
            json={"status": "disabled"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert "disabled" in response.json()["message"]

    def test_delete_user(self, client: TestClient, admin_token: str, test_user: User):
        """测试删除用户"""
        response = client.delete(
            f"/api/admin/users/{test_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert "删除" in response.json()["message"]

    def test_get_user_detail(self, client: TestClient, admin_token: str, test_user: User):
        """测试获取用户详情"""
        response = client.get(
            f"/api/admin/users/{test_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"

    def test_get_user_detail_not_found(self, client: TestClient, admin_token: str):
        """测试用户不存在"""
        response = client.get(
            "/api/admin/users/99999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404


# ==================== 管理员员工管理测试 ====================

class TestAdminStaffManagement:
    """管理员员工管理测试"""

    def test_get_staff_list(self, client: TestClient, admin_token: str, test_admin: Staff):
        """测试获取员工列表"""
        response = client.get(
            "/api/admin/staff",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_create_staff(self, client: TestClient, admin_token: str):
        """测试创建员工"""
        response = client.post(
            "/api/admin/staff",
            json={
                "username": "newoperator",
                "password": "password123",
                "nickname": "新员工",
                "role": "operator"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newoperator"
        assert data["role"] == "operator"

    def test_create_staff_duplicate(self, client: TestClient, admin_token: str, test_admin: Staff):
        """测试创建重复用户名员工"""
        response = client.post(
            "/api/admin/staff",
            json={
                "username": "admin",
                "password": "password123",
                "role": "operator"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400

    def test_update_staff_status(self, client: TestClient, admin_token: str, test_staff: Staff):
        """测试更新员工状态"""
        response = client.put(
            f"/api/admin/staff/{test_staff.id}/status",
            json={"status": "disabled"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200

    def test_update_staff_status_cannot_modify_self(self, client: TestClient, admin_token: str, test_admin: Staff):
        """测试不能修改自己的状态"""
        response = client.put(
            f"/api/admin/staff/{test_admin.id}/status",
            json={"status": "disabled"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400

    def test_delete_staff(self, client: TestClient, admin_token: str, test_staff: Staff):
        """测试删除员工"""
        response = client.delete(
            f"/api/admin/staff/{test_staff.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200

    def test_delete_staff_cannot_delete_self(self, client: TestClient, admin_token: str, test_admin: Staff):
        """测试不能删除自己"""
        response = client.delete(
            f"/api/admin/staff/{test_admin.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400

    def test_get_staff_detail(self, client: TestClient, admin_token: str, test_staff: Staff):
        """测试获取员工详情"""
        response = client.get(
            f"/api/admin/staff/{test_staff.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "operator"


# ==================== 权限测试 ====================

class TestPermission:
    """权限测试"""

    def test_non_admin_cannot_access(self, client: TestClient, user_token: str):
        """测试C端用户无法访问管理接口"""
        response = client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 401  # C端token无法访问B端接口

    def test_operator_cannot_create_staff(self, client: TestClient, staff_token: str):
        """测试运营人员无法创建员工"""
        response = client.post(
            "/api/admin/staff",
            json={
                "username": "newuser",
                "password": "password123",
                "role": "operator"
            },
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 403

    def test_dashboard_stats(self, client: TestClient, admin_token: str):
        """测试获取仪表盘统计"""
        response = client.get(
            "/api/admin/dashboard/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "staff" in data
