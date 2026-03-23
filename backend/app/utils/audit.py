"""
审计日志工具
"""
import json
from datetime import datetime
from typing import Optional, Any
from pathlib import Path

from app.config import settings


class AuditLogger:
    """审计日志记录器"""

    def __init__(self):
        self.log_file = settings.LOGS_DIR / "audit.log"

    def log(
        self,
        action: str,
        user_id: Optional[int] = None,
        user_role: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        detail: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        记录审计日志

        Args:
            action: 操作类型
            user_id: 用户ID
            user_role: 用户角色
            resource_type: 资源类型
            resource_id: 资源ID
            detail: 操作详情
            ip_address: IP地址
            user_agent: 用户代理
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "user_id": user_id,
            "user_role": user_role,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "detail": detail or {},
            "ip_address": ip_address,
            "user_agent": user_agent
        }

        # 追加写入日志文件
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


# 全局审计日志实例
audit_logger = AuditLogger()


# 操作类型常量
class AuditAction:
    """审计操作类型"""
    USER_REGISTER = "user_register"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_STATUS_CHANGE = "user_status_change"
    USER_DELETE = "user_delete"
    CHAT_SEND = "chat_send"
    CHAT_DELETE = "chat_delete"
    CONTRACT_CREATE = "contract_create"
    CONTRACT_UPDATE = "contract_update"
    CONTRACT_GENERATE = "contract_generate"
    CONTRACT_EXPORT = "contract_export"
    CONTRACT_DELETE = "contract_delete"
    CONFIG_UPDATE = "config_update"
    FILE_UPLOAD = "file_upload"
    FILE_DELETE = "file_delete"
