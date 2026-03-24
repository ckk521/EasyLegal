"""
合同草稿API - 草稿保存、恢复、提交
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import json
import uuid

from app.database import get_db
from app.models.document import Contract, FieldDefinition, Template
from app.models.user import User
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/contract-drafts", tags=["合同草稿"])


# ==================== Schemas ====================

class FieldValue(BaseModel):
    """字段值"""
    name: str
    label: str
    value: str = ""
    type: str = "text"
    required: bool = True
    placeholder: str = ""


class ContractDraftCreate(BaseModel):
    """创建草稿"""
    contract_type: str
    field_values: dict = {}


class ContractDraftUpdate(BaseModel):
    """更新草稿"""
    field_values: dict


class ContractDraftResponse(BaseModel):
    """草稿响应"""
    id: int
    contract_no: str
    contract_type: str
    title: Optional[str]
    status: str
    field_values: dict
    fields_definition: List[dict]  # 字段定义
    template_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContractTypeResponse(BaseModel):
    """合同类型响应"""
    contract_type: str
    name: str
    has_template: bool
    has_field_definition: bool


# ==================== APIs ====================

class TemplateContentResponse(BaseModel):
    """模板内容响应"""
    id: int
    name: str
    contract_type: str
    content: str | None
    has_content: bool


@router.get("/template/{contract_type}", response_model=TemplateContentResponse)
async def get_template_by_type(
    contract_type: str,
    db: Session = Depends(get_db)
):
    """
    获取指定合同类型的模板内容（公开接口，无需认证）
    用于C端用户恢复草稿时获取模板
    """
    template = db.query(Template).filter(
        Template.contract_type == contract_type,
        Template.is_active == True
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="未找到该合同类型的模板")

    return TemplateContentResponse(
        id=template.id,
        name=template.name,
        contract_type=template.contract_type,
        content=template.content,
        has_content=bool(template.content)
    )


@router.get("/types", response_model=List[ContractTypeResponse])
async def get_contract_types(
    db: Session = Depends(get_db)
):
    """获取可用的合同类型列表"""
    # 从字段定义获取合同类型
    field_defs = db.query(FieldDefinition).filter(
        FieldDefinition.is_active == True
    ).all()

    # 从模板获取合同类型
    templates = db.query(Template).filter(
        Template.is_active == True
    ).all()

    # 合并去重
    type_map = {}
    for fd in field_defs:
        type_map[fd.contract_type] = {
            "contract_type": fd.contract_type,
            "name": fd.name,
            "has_field_definition": True,
            "has_template": False
        }
    for t in templates:
        if t.contract_type in type_map:
            type_map[t.contract_type]["has_template"] = True
        else:
            type_map[t.contract_type] = {
                "contract_type": t.contract_type,
                "name": t.name,
                "has_field_definition": False,
                "has_template": True
            }

    return list(type_map.values())


@router.get("/list", response_model=List[ContractDraftResponse])
async def list_drafts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户所有草稿列表
    包括未完成和已完成的合同
    """
    contracts = db.query(Contract).filter(
        Contract.user_id == current_user.id
    ).order_by(Contract.updated_at.desc()).all()

    result = []
    for contract in contracts:
        fields_definition = await _get_fields_definition(db, contract.contract_type)
        result.append(ContractDraftResponse(
            id=contract.id,
            contract_no=contract.contract_no,
            contract_type=contract.contract_type,
            title=contract.title,
            status=contract.status,
            field_values=json.loads(contract.field_values) if contract.field_values else {},
            fields_definition=fields_definition,
            template_id=contract.template_id,
            created_at=contract.created_at,
            updated_at=contract.updated_at
        ))

    return result


@router.get("/pending", response_model=Optional[ContractDraftResponse])
async def get_pending_draft(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户未完成的草稿（用于恢复）
    返回最近一个未完成的草稿
    """
    draft = db.query(Contract).filter(
        Contract.user_id == current_user.id,
        Contract.status == "draft"
    ).order_by(Contract.updated_at.desc()).first()

    if not draft:
        return None

    # 获取字段定义
    fields_definition = await _get_fields_definition(db, draft.contract_type)

    return ContractDraftResponse(
        id=draft.id,
        contract_no=draft.contract_no,
        contract_type=draft.contract_type,
        title=draft.title,
        status=draft.status,
        field_values=json.loads(draft.field_values) if draft.field_values else {},
        fields_definition=fields_definition,
        template_id=draft.template_id,
        created_at=draft.created_at,
        updated_at=draft.updated_at
    )


@router.post("", response_model=ContractDraftResponse)
async def create_draft(
    data: ContractDraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新草稿"""
    # 生成合同编号
    contract_no = f"HT{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"

    # 查找模板
    template = db.query(Template).filter(
        Template.contract_type == data.contract_type,
        Template.is_active == True
    ).first()

    draft = Contract(
        contract_no=contract_no,
        user_id=current_user.id,
        contract_type=data.contract_type,
        title=f"{data.contract_type}草稿",
        status="draft",
        field_values=json.dumps(data.field_values, ensure_ascii=False),
        template_id=template.id if template else None
    )

    db.add(draft)
    db.commit()
    db.refresh(draft)

    # 获取字段定义
    fields_definition = await _get_fields_definition(db, draft.contract_type)

    return ContractDraftResponse(
        id=draft.id,
        contract_no=draft.contract_no,
        contract_type=draft.contract_type,
        title=draft.title,
        status=draft.status,
        field_values=json.loads(draft.field_values) if draft.field_values else {},
        fields_definition=fields_definition,
        template_id=draft.template_id,
        created_at=draft.created_at,
        updated_at=draft.updated_at
    )


@router.put("/{draft_id}", response_model=ContractDraftResponse)
async def update_draft(
    draft_id: int,
    data: ContractDraftUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新草稿（自动保存）"""
    draft = db.query(Contract).filter(
        Contract.id == draft_id,
        Contract.user_id == current_user.id,
        Contract.status == "draft"
    ).first()

    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在或已完成")

    # 合并字段值
    existing_values = json.loads(draft.field_values) if draft.field_values else {}
    existing_values.update(data.field_values)
    draft.field_values = json.dumps(existing_values, ensure_ascii=False)

    db.commit()
    db.refresh(draft)

    # 获取字段定义
    fields_definition = await _get_fields_definition(db, draft.contract_type)

    return ContractDraftResponse(
        id=draft.id,
        contract_no=draft.contract_no,
        contract_type=draft.contract_type,
        title=draft.title,
        status=draft.status,
        field_values=json.loads(draft.field_values) if draft.field_values else {},
        fields_definition=fields_definition,
        template_id=draft.template_id,
        created_at=draft.created_at,
        updated_at=draft.updated_at
    )


@router.post("/{draft_id}/complete", response_model=dict)
async def complete_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """完成草稿，生成正式合同"""
    draft = db.query(Contract).filter(
        Contract.id == draft_id,
        Contract.user_id == current_user.id,
        Contract.status == "draft"
    ).first()

    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在或已完成")

    # 验证必填字段
    fields_definition = await _get_fields_definition(db, draft.contract_type)
    field_values = json.loads(draft.field_values) if draft.field_values else {}

    missing_fields = []
    for field in fields_definition:
        if field.get("required") and not field_values.get(field.get("name")):
            missing_fields.append(field.get("label"))

    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"请填写以下必填项：{', '.join(missing_fields)}"
        )

    # 渲染合同内容
    content = await _render_contract(db, draft)

    # 更新状态
    draft.status = "completed"
    draft.content = content
    draft.title = f"{draft.contract_type} - {draft.contract_no}"

    db.commit()
    db.refresh(draft)

    return {
        "message": "合同生成成功",
        "contract_id": draft.id,
        "contract_no": draft.contract_no
    }


@router.delete("/{draft_id}")
async def delete_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除草稿"""
    draft = db.query(Contract).filter(
        Contract.id == draft_id,
        Contract.user_id == current_user.id
    ).first()

    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")

    if draft.status != "draft":
        raise HTTPException(status_code=400, detail="只能删除未完成的草稿")

    db.delete(draft)
    db.commit()

    return {"message": "删除成功"}


@router.get("/{draft_id}", response_model=ContractDraftResponse)
async def get_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取草稿详情"""
    draft = db.query(Contract).filter(
        Contract.id == draft_id,
        Contract.user_id == current_user.id
    ).first()

    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")

    # 获取字段定义
    fields_definition = await _get_fields_definition(db, draft.contract_type)

    return ContractDraftResponse(
        id=draft.id,
        contract_no=draft.contract_no,
        contract_type=draft.contract_type,
        title=draft.title,
        status=draft.status,
        field_values=json.loads(draft.field_values) if draft.field_values else {},
        fields_definition=fields_definition,
        template_id=draft.template_id,
        created_at=draft.created_at,
        updated_at=draft.updated_at
    )


# ==================== Helper Functions ====================

async def _get_fields_definition(db: Session, contract_type: str) -> List[dict]:
    """获取指定合同类型的字段定义"""
    import re

    field_def = db.query(FieldDefinition).filter(
        FieldDefinition.contract_type == contract_type,
        FieldDefinition.is_active == True
    ).first()

    if field_def:
        try:
            return json.loads(field_def.fields)
        except:
            pass

    # 没有字段定义，从模板中提取变量
    template = db.query(Template).filter(
        Template.contract_type == contract_type,
        Template.is_active == True
    ).first()

    if template and template.content:
        # 提取【变量名】格式的变量
        matches = re.findall(r'【([^】]+)】', template.content)
        # 去重并保持顺序
        unique_vars = list(dict.fromkeys(matches))

        fields = []
        for var in unique_vars:
            fields.append({
                "name": var,
                "label": var,
                "type": "text",
                "required": True,
                "placeholder": f"请输入{var}"
            })
        return fields

    # 既没有字段定义也没有模板，返回默认字段
    return [
        {"name": "party_a", "label": "甲方", "type": "text", "required": True, "placeholder": "请输入甲方名称"},
        {"name": "party_b", "label": "乙方", "type": "text", "required": True, "placeholder": "请输入乙方名称"},
        {"name": "content", "label": "合同内容", "type": "textarea", "required": True, "placeholder": "请输入合同主要内容"},
        {"name": "date", "label": "签订日期", "type": "date", "required": True},
    ]


async def _render_contract(db: Session, draft: Contract) -> str:
    """渲染合同内容"""
    template = None
    if draft.template_id:
        template = db.query(Template).filter(Template.id == draft.template_id).first()

    field_values = json.loads(draft.field_values) if draft.field_values else {}

    if template and template.content:
        # 使用模板渲染
        content = template.content
        for key, value in field_values.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
            content = content.replace(f"【{key}】", str(value))
        return content

    # 无模板，生成标准格式
    lines = [
        f"# {draft.contract_type}",
        "",
        f"合同编号：{draft.contract_no}",
        "",
        "---",
        ""
    ]

    for key, value in field_values.items():
        if value:
            lines.append(f"**{key}**：{value}")

    lines.extend([
        "",
        "---",
        "",
        "本合同一式两份，甲乙双方各执一份，具有同等法律效力。",
        "",
        f"签订日期：{datetime.now().strftime('%Y年%m月%d日')}"
    ])

    return "\n".join(lines)
