"""
智能体对话服务 - 基于 LangChain
"""
from typing import AsyncGenerator, List, Optional
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.callbacks import AsyncCallbackHandler
import json

from app.models.config import LLMConfig, RejectScriptConfig, LegalScopeConfig
from app.prompts import PromptLoader
from app.prompts.rejection.templates import REJECTION_TEMPLATES as DEFAULT_REJECTION_TEMPLATES
from app.prompts.system.base import LEGAL_SCOPE_DEFAULT
from app.services.intent_service import IntentService


class StreamingCallbackHandler(AsyncCallbackHandler):
    """流式响应回调处理器"""

    def __init__(self):
        self.tokens: List[str] = []

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """收到新token时调用"""
        self.tokens.append(token)


class ChatService:
    """智能体对话服务"""

    @staticmethod
    def get_llm_client(db: Session) -> Optional[ChatOpenAI]:
        """获取配置好的LLM客户端"""
        config = db.query(LLMConfig).filter(LLMConfig.is_active == True).first()
        if not config:
            return None

        return ChatOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model_name,
            temperature=0.7,
            streaming=True,
        )

    @staticmethod
    def build_messages(history: List[dict], user_message: str, db: Session = None) -> List[BaseMessage]:
        """
        构建消息列表

        优先从数据库读取B端配置，若无配置则使用默认值
        """
        # 获取法律范围配置
        legal_scope = LEGAL_SCOPE_DEFAULT
        if db:
            db_config = db.query(LegalScopeConfig).filter(LegalScopeConfig.is_active == True).first()
            if db_config:
                legal_scope = db_config.scope_description

        # 从提示词加载器获取系统提示词基础部分
        system_prompt = PromptLoader.get_system_prompt(
            include_legal_scope=False,  # 先不包含，手动添加数据库配置
            include_safety=True,
            include_rejection=True
        )

        # 将数据库配置的法律范围插入到系统提示词中
        system_prompt = system_prompt.replace(
            LEGAL_SCOPE_DEFAULT, legal_scope
        ) if LEGAL_SCOPE_DEFAULT in system_prompt else f"{system_prompt}\n\n{legal_scope}"

        messages = [SystemMessage(content=system_prompt)]

        # 添加历史消息
        for msg in history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))

        # 添加当前用户消息
        messages.append(HumanMessage(content=user_message))

        return messages

    @staticmethod
    async def chat_stream(
        db: Session,
        user_message: str,
        history: List[dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式对话

        流程：
        1. 意图识别 - 判断是否法律问题
        2. 非法律问题 - 返回预设拒绝话术
        3. 法律问题 - 调用大模型回答
        """
        if history is None:
            history = []

        llm = ChatService.get_llm_client(db)
        if not llm:
            yield json.dumps({"error": "大模型未配置，请联系管理员"}, ensure_ascii=False)
            return

        # ===== 意图识别 =====
        intent_type, confidence = await IntentService.classify_intent(user_message, db)

        # 如果是非法律问题，直接返回拒绝话术
        if not IntentService.is_legal_intent(intent_type):
            rejection_message = ChatService.get_rejection_message(db)

            # 以流式方式返回拒绝话术
            yield f"data: {json.dumps({'content': rejection_message}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True, 'intent': intent_type, 'rejection': True}, ensure_ascii=False)}\n\n"
            return

        # ===== 法律问题 - 正常对话 =====
        messages = ChatService.build_messages(history, user_message, db)

        try:
            # 流式调用LLM
            async for chunk in llm.astream(messages):
                if chunk.content:
                    # 以SSE格式发送
                    yield f"data: {json.dumps({'content': chunk.content}, ensure_ascii=False)}\n\n"

            # 发送结束标记
            yield f"data: {json.dumps({'done': True, 'intent': intent_type}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    @staticmethod
    async def chat(
        db: Session,
        user_message: str,
        history: List[dict] = None
    ) -> str:
        """
        非流式对话（用于测试）

        同样包含意图识别流程
        """
        if history is None:
            history = []

        llm = ChatService.get_llm_client(db)
        if not llm:
            return "大模型未配置，请联系管理员"

        # 意图识别
        intent_type, confidence = await IntentService.classify_intent(user_message, db)

        # 如果是非法律问题，返回拒绝话术
        if not IntentService.is_legal_intent(intent_type):
            return ChatService.get_rejection_message(db)

        # 法律问题 - 正常对话
        messages = ChatService.build_messages(history, user_message, db)

        try:
            response = await llm.ainvoke(messages)
            return response.content
        except Exception as e:
            return f"对话出错: {str(e)}"

    @staticmethod
    def get_rejection_message(db: Session = None) -> str:
        """
        获取拒绝话术

        优先从数据库读取B端配置，若无配置则使用默认值

        Args:
            db: 数据库会话

        Returns:
            拒绝话术字符串
        """
        # 尝试从数据库获取配置
        if db:
            db_config = db.query(RejectScriptConfig).filter(RejectScriptConfig.is_active == True).first()
            if db_config and db_config.rejection_message:
                return db_config.rejection_message

        # 回退到默认值
        return DEFAULT_REJECTION_TEMPLATES.get("general", "抱歉，我是一款法律咨询服务智能体，只能回答与法律相关的问题。")

    @staticmethod
    def get_service_recommendations() -> str:
        """获取服务推荐列表"""
        return PromptLoader.get_service_recommendations()
