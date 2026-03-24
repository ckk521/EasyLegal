"""
智能体对话服务

服务层职责：
1. 获取LLM配置
2. 创建智能体实例
3. 处理流式输出
4. 管理会话和消息存储

架构：所有用户消息直接走 Agent，由 Agent 决定意图和工具调用
"""

from typing import AsyncGenerator, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
import json

from app.models.config import LLMConfig
from app.models.document import FieldDefinition, Template
from app.models.chat import ChatSession, ChatMessage
from app.agents import ContractAgent
from app.agents.base import AgentContext


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
    def get_or_create_session(db: Session, user_id: int, session_id: int = None) -> ChatSession:
        """获取或创建会话"""
        if session_id:
            session = db.query(ChatSession).filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            ).first()
            if session:
                return session

        # 创建新会话
        session = ChatSession(user_id=user_id)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def save_message(db: Session, session_id: int, role: str, content: str, meta_data: dict = None):
        """保存消息到数据库"""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            meta_data=meta_data
        )
        db.add(message)
        db.commit()

    @staticmethod
    def load_session_history(db: Session, session_id: int, limit: int = 50) -> List[dict]:
        """加载会话历史消息"""
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.asc()).limit(limit).all()

        return [{"role": m.role, "content": m.content} for m in messages]

    @staticmethod
    def get_user_sessions(db: Session, user_id: int, limit: int = 20) -> List[dict]:
        """获取用户的会话列表"""
        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.status == 'active'
        ).order_by(ChatSession.updated_at.desc()).limit(limit).all()

        result = []
        for s in sessions:
            # 获取最后一条消息作为预览
            last_msg = db.query(ChatMessage).filter(
                ChatMessage.session_id == s.id
            ).order_by(ChatMessage.created_at.desc()).first()

            result.append({
                "id": s.id,
                "title": s.title or (last_msg.content[:50] if last_msg and last_msg.content else "新对话"),
                "contract_id": s.contract_id,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            })

        return result

    @staticmethod
    def get_session_detail(db: Session, session_id: int, user_id: int) -> Optional[dict]:
        """获取会话详情（含消息历史）"""
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id
        ).first()

        if not session:
            return None

        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.asc()).all()

        return {
            "id": session.id,
            "title": session.title,
            "contract_id": session.contract_id,
            "status": session.status,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "metadata": m.meta_data,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ]
        }

    @staticmethod
    def delete_session(db: Session, session_id: int, user_id: int) -> bool:
        """删除会话"""
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id
        ).first()

        if not session:
            return False

        db.delete(session)
        db.commit()
        return True

    @staticmethod
    async def chat_stream(
        db: Session,
        user_message: str,
        history: List[dict] = None,
        user_id: int = None,
        session_id: int = None
    ) -> AsyncGenerator[str, None]:
        """
        流式对话

        主要入口方法：所有用户消息直接走 Agent

        Args:
            db: 数据库会话
            user_message: 用户消息
            history: 对话历史（可选，如果不传则从数据库加载）
            user_id: 用户ID
            session_id: 会话ID（可选，不传则创建新会话）

        Yields:
            SSE格式的响应
        """
        # 1. 获取或创建会话
        session = ChatService.get_or_create_session(db, user_id, session_id)

        # 2. 加载历史消息（如果前端没有传）
        if history is None:
            history = ChatService.load_session_history(db, session.id)

        # 3. 保存用户消息
        ChatService.save_message(db, session.id, "user", user_message)

        # 4. 发送会话ID给前端
        yield f"data: {json.dumps({'session_id': session.id}, ensure_ascii=False)}\n\n"

        # 5. 获取LLM
        llm = ChatService.get_llm_client(db)
        if not llm:
            yield f"data: {json.dumps({'error': '大模型未配置，请联系管理员'}, ensure_ascii=False)}\n\n"
            return

        # 6. 所有消息直接走 Agent（Agent 自己判断意图和法律范围）
        ai_content = ""
        tool_metadata = None

        async for event in ChatService._handle_with_agent(db, llm, user_message, history, user_id, session.id):
            # 收集AI回复内容
            if event.startswith("data: "):
                try:
                    data = json.loads(event[6:].strip())
                    if data.get("content"):
                        ai_content += data["content"]
                    if data.get("type"):
                        tool_metadata = tool_metadata or {}
                        tool_metadata[data["type"]] = data.get("data")
                except:
                    pass
            yield event

        # 7. 保存AI回复（在流式输出完成后）
        if ai_content or tool_metadata:
            ChatService.save_message(db, session.id, "assistant", ai_content, tool_metadata)

        # 8. 更新会话标题（如果是第一条消息）
        if len(history) == 0 and user_message:
            session.title = user_message[:50]
            db.commit()

    @staticmethod
    async def _handle_with_agent(
        db: Session,
        llm: ChatOpenAI,
        user_message: str,
        history: List[dict],
        user_id: int,
        session_id: int
    ) -> AsyncGenerator[str, None]:
        """
        使用 Agent 处理所有用户消息

        Agent 自己判断：
        - 是否打招呼/非法务问题/法务相关
        - 用户意图（法律咨询/合同状态查询/合同相关）
        - 是否需要调用工具
        """
        # 创建智能体
        agent = ContractAgent(llm)

        # 设置上下文
        context = AgentContext(db=db, user_id=user_id)
        agent.set_context(context)

        # 从数据库加载配置
        agent.load_config_from_db()

        try:
            # 运行智能体
            result = await agent.run_with_tools(user_message, history)

            # 发送文本回复
            if result.get("content"):
                yield f"data: {json.dumps({'content': result['content']}, ensure_ascii=False)}\n\n"

            # 处理工具调用结果
            if result.get("tool_results"):
                for tool_result in result["tool_results"]:
                    if tool_result.get("success") and tool_result.get("result"):
                        tool_data = tool_result["result"]

                        # 根据工具返回的 action 处理
                        if isinstance(tool_data, dict):
                            action = tool_data.get("action")
                            data = tool_data.get("data", {})

                            # 如果没有文本内容，根据工具结果生成默认回复
                            if not result.get("content"):
                                default_message = data.get("message", "好的，请继续。")
                                yield f"data: {json.dumps({'content': default_message}, ensure_ascii=False)}\n\n"

                            # 合同相关表单
                            if action == "collect_contract_info":
                                yield f"data: {json.dumps({'type': 'contract_form', 'form': data}, ensure_ascii=False)}\n\n"

                            # 询问合同类型
                            elif action == "ask_contract_type":
                                yield f"data: {json.dumps({'type': 'contract_type_selection', 'data': data}, ensure_ascii=False)}\n\n"

                            # 显示模板列表
                            elif action == "show_template_list":
                                yield f"data: {json.dumps({'type': 'template_list', 'data': data}, ensure_ascii=False)}\n\n"

                            # 没有模板，引导信息收集
                            elif action == "no_template_available":
                                yield f"data: {json.dumps({'type': 'no_template', 'data': data}, ensure_ascii=False)}\n\n"

                            # 草稿保存成功
                            elif action == "draft_saved":
                                yield f"data: {json.dumps({'type': 'draft_saved', 'data': data}, ensure_ascii=False)}\n\n"

                            # 合同导出成功
                            elif action == "contract_exported":
                                yield f"data: {json.dumps({'type': 'contract_exported', 'data': data}, ensure_ascii=False)}\n\n"

                            # 用户合同列表
                            elif action == "user_contracts_list":
                                yield f"data: {json.dumps({'type': 'user_contracts', 'data': data}, ensure_ascii=False)}\n\n"

                            # RAG检索结果
                            elif action == "rag_search_result":
                                yield f"data: {json.dumps({'type': 'rag_result', 'data': data}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    @staticmethod
    async def chat(
        db: Session,
        user_message: str,
        history: List[dict] = None,
        user_id: int = None
    ) -> str:
        """非流式对话（用于测试）"""
        if history is None:
            history = []

        llm = ChatService.get_llm_client(db)
        if not llm:
            return "大模型未配置，请联系管理员"

        try:
            agent = ContractAgent(llm)
            context = AgentContext(db=db, user_id=user_id)
            agent.set_context(context)
            agent.load_config_from_db()

            result = await agent.run_with_tools(user_message, history)

            content = result.get("content", "")

            # 如果有工具调用结果，附加信息
            if result.get("tool_results"):
                for tool_result in result["tool_results"]:
                    if tool_result.get("success") and tool_result.get("result"):
                        tool_data = tool_result["result"]
                        if isinstance(tool_data, dict):
                            data = tool_data.get("data", {})
                            if data.get("message"):
                                content += f"\n[系统提示: {data['message']}]"

            return content if content else "处理完成"
        except Exception as e:
            return f"对话出错: {str(e)}"

    @staticmethod
    async def get_contract_form(contract_type: str, db: Session, template_id: int = None) -> Dict[str, Any]:
        """获取合同生成表单数据"""
        from app.agents.tools.contract_tools import execute_get_contract_form

        result = execute_get_contract_form(contract_type, template_id, db=db)

        if result.get("success"):
            return result.get("data", {})

        return {
            "contract_type": contract_type,
            "contract_type_name": contract_type,
            "has_template": False,
            "template_id": None,
            "fields": [],
            "template_content": "",
        }

    @staticmethod
    async def get_template_form(template_id: int, db: Session) -> Dict[str, Any]:
        """根据模板ID获取表单数据"""
        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            raise ValueError(f"模板ID {template_id} 不存在")

        # 查询字段定义
        field_def = db.query(FieldDefinition).filter(
            FieldDefinition.contract_type == template.contract_type,
            FieldDefinition.is_active == True
        ).first()

        fields = []
        if field_def:
            try:
                fields = json.loads(field_def.fields)
            except:
                pass

        return {
            "contract_type": template.contract_type,
            "contract_type_name": template.name,
            "has_template": True,
            "template_id": template.id,
            "fields": fields,
            "template_content": template.content or "",
        }
