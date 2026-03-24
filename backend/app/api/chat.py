"""
C端对话 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import json

from app.database import get_db
from app.models.user import User
from app.utils.security import get_current_user
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["对话"])


class Message(BaseModel):
    """消息模型"""
    role: str  # user 或 assistant
    content: str


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    history: Optional[List[Message]] = []
    session_id: Optional[int] = None  # 会话ID，不传则创建新会话


class ChatResponse(BaseModel):
    """对话响应"""
    content: str


class SessionResponse(BaseModel):
    """会话响应"""
    id: int
    title: str
    contract_id: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]


class SessionDetailResponse(BaseModel):
    """会话详情响应"""
    id: int
    title: Optional[str]
    contract_id: Optional[int]
    status: str
    created_at: Optional[str]
    updated_at: Optional[str]
    messages: List[dict]


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    流式对话接口 (SSE)

    客户端通过 SSE 接收流式响应
    """
    # DEBUG: 打印请求信息
    import sys
    print(f"[DEBUG] chat_stream called, user_id={current_user.id}, message={request.message}, session_id={request.session_id}", file=sys.stderr, flush=True)

    # 转换历史消息格式（如果有）
    history = None
    if request.history:
        history = [{"role": msg.role, "content": msg.content} for msg in request.history]

    return StreamingResponse(
        ChatService.chat_stream(db, request.message, history, current_user.id, request.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用nginx缓冲
        }
    )


@router.post("/message", response_model=ChatResponse)
async def chat_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    非流式对话接口（用于测试）
    """
    history = [{"role": msg.role, "content": msg.content} for msg in request.history]

    content = await ChatService.chat(db, request.message, history, current_user.id)

    return ChatResponse(content=content)


@router.get("/sessions", response_model=List[SessionResponse])
async def get_sessions(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的会话列表
    """
    sessions = ChatService.get_user_sessions(db, current_user.id, limit)
    return sessions


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取会话详情（含消息历史）
    """
    session = ChatService.get_session_detail(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除会话
    """
    success = ChatService.delete_session(db, session_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True}


@router.get("/check-llm")
async def check_llm_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """检查LLM是否已配置"""
    from app.models.config import LLMConfig

    config = db.query(LLMConfig).filter(LLMConfig.is_active == True).first()

    return {
        "configured": config is not None,
        "model_name": config.model_name if config else None
    }
