"""
智能合同审核平台 - FastAPI入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, SessionLocal
from app.services.staff_service import StaffService
from app.api import auth, admin, staff_auth, config, chat, document, contract_draft, contract_config, contract_review


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    init_db()

    # 创建默认admin账号（B端员工）
    db = SessionLocal()
    try:
        StaffService.create_admin_if_not_exists(db)

        # 预加载 Embedding 模型（避免第一次请求慢）
        print("Preloading embedding model...")
        from app.services.rag_service import RAGService
        RAGService.get_embeddings(db)
        print("Embedding model loaded.")
    finally:
        db.close()

    yield

    # 关闭时清理资源（如有需要）


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="智能合同审核平台后端API",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)        # C端用户认证
app.include_router(staff_auth.router)  # B端员工认证
app.include_router(admin.router)       # B端管理
app.include_router(config.router)      # 配置管理
app.include_router(chat.router)        # C端对话
app.include_router(document.router)    # 文档管理
app.include_router(contract_draft.router)  # 合同草稿
app.include_router(contract_config.router)  # 合同配置管理
app.include_router(contract_review.router)  # 合同审核


@app.get("/")
def root():
    """根路径"""
    return {
        "message": f"欢迎使用{settings.APP_NAME}API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
