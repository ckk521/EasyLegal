"""
法务智能体工具定义

根据 PRD §10.1.3 详细调用流程设计。
"""

from typing import Optional, Dict, Any, List
from langchain_core.tools import tool
import json


# ==================== 工具定义 ====================

@tool
def rag_search(query: str) -> dict:
    """
    RAG检索知识库。

    当用户咨询法律问题（非合同生成）时调用此工具。
    例如用户问"违约责任怎么约定"、"这个条款什么意思"。

    Args:
        query: 用户的问题或查询关键词

    Returns:
        包含检索结果的字典
    """
    return {
        "action": "rag_search",
        "query": query
    }


@tool
def get_user_contracts(status: str = "") -> dict:
    """
    获取用户的历史合同列表。

    当用户查询已有合同状态时调用此工具。
    例如用户问"我的合同怎么样了"、"之前的合同呢"。

    Args:
        status: 可选，筛选指定状态的合同（draft/pending/completed）

    Returns:
        包含用户合同列表的字典
    """
    return {
        "action": "get_user_contracts",
        "status": status if status else None
    }


@tool
def ask_contract_type() -> dict:
    """
    询问用户需要什么类型的合同。

    当用户想生成合同但没有说明具体类型时调用此工具。
    例如用户说"我要写合同"或"帮我起草一份合同"。

    Returns:
        包含可选合同类型列表的字典
    """
    return {
        "action": "ask_contract_type"
    }


@tool
def get_template_list(contract_type: str) -> dict:
    """
    获取合同模板列表。

    当用户明确说了具体的合同类型后调用此工具。
    例如用户说"我要写租赁合同"、"帮我生成借款合同"。

    Args:
        contract_type: 合同类型，如：租赁合同、借款合同、劳动合同等

    Returns:
        包含模板列表的字典
    """
    return {
        "action": "get_template_list",
        "contract_type": contract_type
    }


@tool
def get_contract_form(contract_type: str, template_id: int = 0) -> dict:
    """
    获取合同生成表单。

    当用户确定要生成某种类型的合同，或选择使用某个模板时调用此工具。
    返回合同字段定义和模板内容。

    Args:
        contract_type: 合同类型
        template_id: 模板ID（可选，用户选择特定模板时传入）

    Returns:
        包含表单字段和模板内容的字典
    """
    return {
        "action": "get_contract_form",
        "contract_type": contract_type,
        "template_id": template_id if template_id else None
    }


@tool
def save_contract_draft(contract_type: str, fields_data: str, template_id: int = 0) -> dict:
    """
    保存合同草稿。

    当用户填写过程中需要保存草稿时调用此工具。

    Args:
        contract_type: 合同类型
        fields_data: 合同字段数据（JSON字符串）
        template_id: 模板ID（可选）

    Returns:
        包含草稿ID的字典
    """
    return {
        "action": "save_contract_draft",
        "contract_type": contract_type,
        "fields_data": fields_data,
        "template_id": template_id if template_id else None
    }


@tool
def export_contract(draft_id: int, format: str = "pdf") -> dict:
    """
    导出合同文档。

    当用户确认合同内容后需要导出时调用此工具。

    Args:
        draft_id: 草稿/合同ID
        format: 导出格式，pdf 或 word

    Returns:
        包含下载链接的字典
    """
    return {
        "action": "export_contract",
        "draft_id": draft_id,
        "format": format
    }


# ==================== 工具执行函数 ====================

def execute_rag_search(query: str, db=None) -> Dict[str, Any]:
    """执行RAG检索"""
    # TODO: 集成RAG检索系统
    # 目前返回占位结果，后续对接Chroma向量库
    return {
        "success": True,
        "action": "rag_search_result",
        "data": {
            "query": query,
            "results": [],
            "answer": f"关于「{query}」的问题，我正在检索知识库...",
            "message": "RAG检索功能待集成"
        }
    }


def execute_get_user_contracts(status: str = None, db=None, user_id: int = None) -> Dict[str, Any]:
    """执行查询用户合同列表"""
    if db is None:
        return {"success": False, "error": "数据库会话未注入"}

    from app.models.contract_draft import ContractDraft

    query = db.query(ContractDraft).filter(ContractDraft.user_id == user_id)
    if status:
        query = query.filter(ContractDraft.status == status)

    contracts = query.order_by(ContractDraft.updated_at.desc()).all()

    contract_list = [
        {
            "id": c.id,
            "contract_type": c.contract_type,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in contracts
    ]

    return {
        "success": True,
        "action": "user_contracts_list",
        "data": {
            "contracts": contract_list,
            "total": len(contract_list),
            "message": f"找到 {len(contract_list)} 份合同" if contract_list else "暂无合同记录"
        }
    }


def execute_ask_contract_type(db=None) -> Dict[str, Any]:
    """执行询问合同类型"""
    # 尝试从数据库获取已配置的合同类型
    available_types = [
        {"type": "租赁合同", "description": "房屋、车辆等租赁"},
        {"type": "借款合同", "description": "个人或企业间借款"},
        {"type": "劳动合同", "description": "用人单位与劳动者"},
        {"type": "买卖合同", "description": "商品、房产等买卖"},
        {"type": "服务合同", "description": "咨询服务、技术服务等"},
    ]

    return {
        "success": True,
        "action": "ask_contract_type",
        "data": {
            "available_types": available_types,
            "message": "请问您需要什么类型的合同？"
        }
    }


def execute_get_template_list(contract_type: str, db=None) -> Dict[str, Any]:
    """执行获取模板列表"""
    if db is None:
        return {"success": False, "error": "数据库会话未注入"}

    from app.models.document import Template

    templates = db.query(Template).filter(
        Template.contract_type == contract_type,
        Template.is_active == True
    ).all()

    template_list = [
        {
            "id": t.id,
            "name": t.name,
            "contract_type": t.contract_type,
            "description": t.description or "",
        }
        for t in templates
    ]

    if len(template_list) == 0:
        return {
            "success": True,
            "action": "no_template_available",
            "data": {
                "templates": [],
                "has_templates": False,
                "contract_type": contract_type,
                "message": f"暂时没有{contract_type}的模板，我们可以一起完成合同信息收集。"
            }
        }

    return {
        "success": True,
        "action": "show_template_list",
        "data": {
            "templates": template_list,
            "has_templates": True,
            "contract_type": contract_type,
            "message": f"找到 {len(template_list)} 个{contract_type}模板"
        }
    }


def execute_get_contract_form(contract_type: str, template_id: int = None, db=None) -> Dict[str, Any]:
    """执行获取合同表单"""
    if db is None:
        return {"success": False, "error": "数据库会话未注入"}

    from app.models.document import FieldDefinition, Template

    # 获取字段定义
    field_def = db.query(FieldDefinition).filter(
        FieldDefinition.contract_type == contract_type,
        FieldDefinition.is_active == True
    ).first()

    # 获取模板（优先使用指定的template_id）
    template = None
    if template_id:
        template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        template = db.query(Template).filter(
            Template.contract_type == contract_type,
            Template.is_active == True
        ).first()

    # 解析字段
    fields = []
    if field_def:
        try:
            fields = json.loads(field_def.fields)
        except:
            pass

    if not fields:
        fields = _get_default_fields(contract_type)

    # 获取模板内容
    template_content = None
    if template and template.content:
        template_content = template.content
    else:
        template_content = _get_default_template(contract_type)

    return {
        "success": True,
        "action": "collect_contract_info",
        "data": {
            "contract_type": contract_type,
            "contract_type_name": field_def.name if field_def else contract_type,
            "template_id": template.id if template else None,
            "has_template": template is not None,
            "fields": fields,
            "template_content": template_content,
            "message": f"好的，我来帮您准备{contract_type}。"
        }
    }


def execute_save_contract_draft(
    contract_type: str,
    fields_data: str,
    template_id: int = None,
    db=None,
    user_id: int = None
) -> Dict[str, Any]:
    """执行保存合同草稿"""
    if db is None:
        return {"success": False, "error": "数据库会话未注入"}

    from app.models.contract_draft import ContractDraft

    try:
        fields_dict = json.loads(fields_data) if isinstance(fields_data, str) else fields_data
    except:
        fields_dict = {}

    draft = ContractDraft(
        user_id=user_id,
        contract_type=contract_type,
        template_id=template_id,
        fields_definition=json.dumps(fields_dict),
        status="draft",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    return {
        "success": True,
        "action": "draft_saved",
        "data": {
            "draft_id": draft.id,
            "message": "草稿保存成功"
        }
    }


def execute_export_contract(draft_id: int, format: str = "pdf", db=None) -> Dict[str, Any]:
    """执行导出合同"""
    if db is None:
        return {"success": False, "error": "数据库会话未注入"}

    from app.models.contract_draft import ContractDraft

    draft = db.query(ContractDraft).filter(ContractDraft.id == draft_id).first()
    if not draft:
        return {"success": False, "error": "草稿不存在"}

    # TODO: 实际的文档生成逻辑
    return {
        "success": True,
        "action": "contract_exported",
        "data": {
            "draft_id": draft_id,
            "format": format,
            "download_url": f"/api/contracts/{draft_id}/download?format={format}",
            "message": f"合同已生成，点击下载{format.upper()}文件"
        }
    }


# ==================== 辅助函数 ====================

def _get_default_fields(contract_type: str) -> List[Dict]:
    """获取默认字段定义"""
    if "租赁" in contract_type:
        return [
            {"name": "party_a", "label": "甲方（出租方）", "type": "text", "required": True},
            {"name": "party_b", "label": "乙方（承租方）", "type": "text", "required": True},
            {"name": "property_address", "label": "房屋地址", "type": "text", "required": True},
            {"name": "rent_price", "label": "月租金", "type": "text", "required": True},
            {"name": "start_date", "label": "租赁开始日期", "type": "date", "required": True},
            {"name": "end_date", "label": "租赁结束日期", "type": "date", "required": True},
        ]
    if "借款" in contract_type:
        return [
            {"name": "lender", "label": "出借人", "type": "text", "required": True},
            {"name": "borrower", "label": "借款人", "type": "text", "required": True},
            {"name": "loan_amount", "label": "借款金额", "type": "text", "required": True},
            {"name": "loan_date", "label": "借款日期", "type": "date", "required": True},
            {"name": "repayment_date", "label": "还款日期", "type": "date", "required": True},
        ]
    return [
        {"name": "party_a", "label": "甲方", "type": "text", "required": True},
        {"name": "party_b", "label": "乙方", "type": "text", "required": True},
    ]


def _get_default_template(contract_type: str) -> str:
    """获取默认模板内容"""
    if "租赁" in contract_type:
        return """# 房屋租赁合同

出租方（甲方）：【甲方名称】
承租方（乙方）：【乙方名称】

房屋地址：【房屋地址】
月租金：【月租金】元
租赁期限：【开始日期】至【结束日期】

甲方签字：________________  日期：________年____月____日
乙方签字：________________  日期：________年____月____日
"""
    return f"# {contract_type}\n\n请填写相关信息后生成合同。"


# ==================== 工具列表 ====================

def create_contract_tools():
    """创建法务智能体工具列表"""
    return [
        rag_search,
        get_user_contracts,
        ask_contract_type,
        get_template_list,
        get_contract_form,
        save_contract_draft,
        export_contract,
    ]


# 工具名称到执行函数的映射
TOOL_EXECUTORS = {
    "rag_search": execute_rag_search,
    "get_user_contracts": execute_get_user_contracts,
    "ask_contract_type": execute_ask_contract_type,
    "get_template_list": execute_get_template_list,
    "get_contract_form": execute_get_contract_form,
    "save_contract_draft": execute_save_contract_draft,
    "export_contract": execute_export_contract,
}
