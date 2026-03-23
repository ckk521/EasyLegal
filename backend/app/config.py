"""
应用配置管理
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    APP_NAME: str = "智能合同审核平台"
    DEBUG: bool = True

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./data/easyagent.db"

    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7

    # 文件存储路径
    DATA_DIR: Path = Path(__file__).parent.parent / "data"
    TEMPLATES_DIR: Path = DATA_DIR / "templates"
    DOCUMENTS_DIR: Path = DATA_DIR / "documents"
    CONTRACTS_DIR: Path = DATA_DIR / "contracts"
    LOGS_DIR: Path = DATA_DIR / "logs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保数据目录存在
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        self.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        self.CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
