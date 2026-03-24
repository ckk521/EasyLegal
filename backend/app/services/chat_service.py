"""
智能体对话服务 - 基于 LangChain
"""
from typing import AsyncGenerator, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.callbacks import AsyncCallbackHandler
import json
import re

from app.models.config import LLMConfig, RejectScriptConfig, LegalScopeConfig
from app.models.document import FieldDefinition, Template
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

        # ===== 合同生成意图 - 返回表单 =====
        if intent_type == "contract_generation":
            form_data = await ChatService.get_contract_form(user_message, db)
            yield f"data: {json.dumps({'type': 'contract_form', 'form': form_data}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True, 'intent': intent_type}, ensure_ascii=False)}\n\n"
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

    @staticmethod
    async def get_contract_form(user_message: str, db: Session) -> Dict[str, Any]:
        """
        获取合同生成表单数据

        Args:
            user_message: 用户消息
            db: 数据库会话

        Returns:
            表单配置数据
        """
        # 从用户消息中提取合同类型
        contract_type = ChatService._extract_contract_type(user_message)

        # 查询字段定义
        field_def = db.query(FieldDefinition).filter(
            FieldDefinition.contract_type == contract_type,
            FieldDefinition.is_active == True
        ).first()

        # 查询模板
        template = db.query(Template).filter(
            Template.contract_type == contract_type,
            Template.is_active == True
        ).first()

        # 构建字段列表
        fields = []
        if field_def:
            try:
                fields = json.loads(field_def.fields)
            except:
                pass

        if not fields:
            # 默认字段
            fields = [
                {"name": "party_a", "label": "甲方（出租方）", "type": "text", "required": True, "placeholder": "请输入甲方名称"},
                {"name": "party_b", "label": "乙方（承租方）", "type": "text", "required": True, "placeholder": "请输入乙方名称"},
                {"name": "id_card_a", "label": "甲方身份证号", "type": "text", "required": False, "placeholder": "请输入甲方身份证号"},
                {"name": "id_card_b", "label": "乙方身份证号", "type": "text", "required": False, "placeholder": "请输入乙方身份证号"},
                {"name": "property_address", "label": "房屋地址", "type": "text", "required": True, "placeholder": "请输入房屋详细地址"},
                {"name": "area", "label": "房屋面积", "type": "text", "required": False, "placeholder": "如：50平方米"},
                {"name": "rent_price", "label": "月租金", "type": "text", "required": True, "placeholder": "如：3000元/月"},
                {"name": "deposit", "label": "押金", "type": "text", "required": False, "placeholder": "如：押一付三"},
                {"name": "start_date", "label": "租赁开始日期", "type": "date", "required": True},
                {"name": "end_date", "label": "租赁结束日期", "type": "date", "required": True},
                {"name": "payment_method", "label": "付款方式", "type": "select", "required": False, "options": ["月付", "季付", "半年付", "年付"]},
                {"name": "contact_phone", "label": "联系电话", "type": "text", "required": False, "placeholder": "请输入联系电话"},
                {"name": "remarks", "label": "备注", "type": "textarea", "required": False, "placeholder": "其他约定事项"},
            ]

        # 获取模板内容（如果有）
        template_content = None
        if template and template.content:
            template_content = template.content
        else:
            # 使用默认模板
            template_content = ChatService._get_default_template(contract_type, fields)

        return {
            "contract_type": contract_type,
            "contract_type_name": field_def.name if field_def else f"{contract_type}合同",
            "has_template": template is not None,
            "template_id": template.id if template else None,
            "fields": fields,
            "template_content": template_content,
            "greeting": f"好的，我将帮您生成一份{contract_type}合同。请填写以下信息："
        }

    @staticmethod
    def _get_default_template(contract_type: str, fields: List[dict]) -> str:
        """获取默认合同模板"""
        # 租赁合同模板
        if contract_type == "租赁合同":
            return """# 房屋租赁合同

出租方（甲方）：【甲方名称】
身份证号码：【甲方身份证号】
联系电话：【甲方电话】

承租方（乙方）：【乙方名称】
身份证号码：【乙方身份证号】
联系电话：【乙方电话】

根据《中华人民共和国民法典》及相关法律法规的规定，甲、乙双方在平等、自愿的基础上，就房屋租赁事宜达成如下协议：

## 第一条 房屋基本情况

1.1 房屋坐落：【房屋地址】

1.2 房屋建筑面积：【房屋面积】平方米

1.3 房屋用途：居住

## 第二条 租赁期限

2.1 租赁期限自【租赁开始日期】起至【租赁结束日期】止。

2.2 租赁期满，如乙方要求续租，则必须在租赁期满前一个月向甲方提出书面意向，经甲方同意后，重新签订租赁合同。

## 第三条 租金及支付方式

3.1 该房屋每月租金为人民币【月租金】元整（¥：【月租金】）。

3.2 押金为人民币【押金】元整，于签订本合同时一次性支付。

3.3 付款方式：【付款方式】。

## 第四条 其他约定

【备注】

## 第五条 签署

本合同一式两份，甲、乙双方各执一份，自双方签字之日起生效。

甲方签字：__________________    日期：【签订日期】

乙方签字：__________________    日期：【签订日期】
"""
        # 通用合同模板（买卖合同、借款合同、或其他未定义类型）
        else:
            return """# 合同

甲方：【甲方名称】
地址：【甲方地址】
联系电话：【甲方电话】

乙方：【乙方名称】
地址：【乙方地址】
联系电话：【乙方电话】

根据《中华人民共和国民法典》及相关法律法规的规定，甲、乙双方在平等、自愿的基础上，经友好协商，达成如下协议：

## 第一条 合同标的

【合同主要内容】

## 第二条 合同金额及支付方式

2.1 合同总金额为人民币【合同金额】元整。

2.2 支付方式：【支付方式】。

## 第三条 双方权利义务

3.1 甲方的权利和义务：【甲方权利义务】

3.2 乙方的权利和义务：【乙方权利义务】

## 第四条 合同期限

本合同有效期自【开始日期】起至【结束日期】止。

## 第五条 违约责任

任何一方违反本合同约定的，应承担违约责任，向守约方支付违约金人民币【违约金】元。

## 第六条 争议解决

因履行本合同发生的争议，双方应协商解决；协商不成的，可向合同签订地人民法院提起诉讼。

## 第七条 其他约定

【其他约定事项】

## 第八条 签署

本合同一式两份，甲、乙双方各执一份，自双方签字（盖章）之日起生效。

甲方（盖章）：__________________    日期：【签订日期】

乙方（盖章）：__________________    日期：【签订日期】
"""

    @staticmethod
    def _extract_contract_type(user_message: str) -> str:
        """
        从用户消息中提取合同类型

        Args:
            user_message: 用户消息

        Returns:
            合同类型字符串
        """
        # 合同类型映射
        type_patterns = {
            "租赁合同": r"租赁|租房|出租|承租|房租",
            "买卖合同": r"买卖|购买|出售|购房|卖房|二手房",
            "借款合同": r"借款|借贷|贷款|借条|欠条",
            "劳动合同": r"劳动|雇佣|入职|工作",
            "服务合同": r"服务|咨询|代理",
            "合作协议": r"合作|合伙|联合",
            "装修合同": r"装修|装饰|改造",
            "运输合同": r"运输|货运|物流",
            "保管合同": r"保管|寄存|存储",
            "赠与合同": r"赠与|赠送|捐赠",
        }

        message_lower = user_message.lower()

        for contract_type, pattern in type_patterns.items():
            if re.search(pattern, message_lower):
                return contract_type

        # 未匹配到具体类型，返回通用合同
        return "通用合同"
