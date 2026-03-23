"""
意图识别服务 - 判断用户消息是否属于法律范畴
"""
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json
import re

from app.models.config import LLMConfig, RejectScriptConfig, LegalScopeConfig
from app.prompts.intents.recognition import INTENT_RECOGNITION_SYSTEM


class IntentService:
    """意图识别服务"""

    # 意图类型定义
    INTENT_TYPES = {
        # 法律相关
        "legal_consultation": "法律咨询",
        "contract_generation": "合同生成",
        "contract_review": "合同审核",
        "legal_knowledge": "法律知识查询",
        # 非法律相关
        "small_talk": "闲聊",
        "medical": "医疗健康",
        "investment": "投资理财",
        "technical": "技术问题",
        "daily_info": "日常信息",
        "entertainment": "娱乐",
        "other_non_legal": "其他非法律问题"
    }

    # 法律相关意图
    LEGAL_INTENTS = {"legal_consultation", "contract_generation", "contract_review", "legal_knowledge"}

    # 非法律意图类型（需要拒绝）
    NON_LEGAL_INTENTS = {"small_talk", "medical", "investment", "technical", "daily_info", "entertainment", "other_non_legal"}

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
            temperature=0.1,  # 低温度，更确定的输出
            streaming=False,
        )

    @staticmethod
    async def classify_intent(user_message: str, db: Session) -> Tuple[str, float]:
        """
        分类用户意图

        Args:
            user_message: 用户消息
            db: 数据库会话

        Returns:
            (intent_type, confidence): 意图类型和置信度
        """
        llm = IntentService.get_llm_client(db)
        if not llm:
            # 无LLM配置，默认为法律咨询
            return "legal_consultation", 0.5

        # 获取法律范围配置
        legal_scope = ""
        db_config = db.query(LegalScopeConfig).filter(LegalScopeConfig.is_active == True).first()
        if db_config:
            legal_scope = db_config.scope_description

        # 构建提示词
        system_prompt = INTENT_RECOGNITION_SYSTEM.format(
            legal_scope=legal_scope[:500] if legal_scope else "法律相关问题"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"请判断以下用户消息的意图：\n\n{user_message}")
        ]

        try:
            response = await llm.ainvoke(messages)
            content = response.content.strip()

            # 解析返回的JSON
            # 尝试提取JSON部分
            json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                intent_type = result.get("intent", "other_non_legal")
                confidence = result.get("confidence", 0.5)
                return intent_type, confidence

            # 如果无法解析JSON，尝试从文本中提取意图
            for intent_key in IntentService.INTENT_TYPES:
                if intent_key in content.lower():
                    return intent_key, 0.7

            return "other_non_legal", 0.5

        except Exception as e:
            print(f"意图识别出错: {e}")
            return "legal_consultation", 0.5  # 出错时默认为法律咨询

    @staticmethod
    def is_legal_intent(intent_type: str) -> bool:
        """判断是否为法律相关意图"""
        return intent_type not in IntentService.NON_LEGAL_INTENTS
