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
    session_id: Optional[int] = None  # 关联的会话ID


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
    session_id: Optional[int] = None  # 关联的会话ID
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
            session_id=contract.session_id,
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
        session_id=draft.session_id,
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
        template_id=template.id if template else None,
        session_id=data.session_id  # 保存关联的会话ID
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
        session_id=draft.session_id,
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
        session_id=draft.session_id,
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


class ContractContentResponse(BaseModel):
    """合同内容响应"""
    id: int
    contract_no: str
    contract_type: str
    title: Optional[str]
    status: str
    content: str
    field_values: dict
    created_at: datetime
    updated_at: datetime


# 注意：这些带子路径的路由必须放在 /{draft_id} 之前
@router.get("/{draft_id}/content", response_model=ContractContentResponse)
async def get_contract_content(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取合同详情内容
    返回已渲染的合同文本
    """
    contract = db.query(Contract).filter(
        Contract.id == draft_id,
        Contract.user_id == current_user.id
    ).first()

    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    # 如果已完成，直接返回渲染后的内容
    if contract.status == "completed" and contract.content:
        content = contract.content
    else:
        # 否则实时渲染
        content = await _render_contract(db, contract)

    return ContractContentResponse(
        id=contract.id,
        contract_no=contract.contract_no,
        contract_type=contract.contract_type,
        title=contract.title,
        status=contract.status,
        content=content,
        field_values=json.loads(contract.field_values) if contract.field_values else {},
        created_at=contract.created_at,
        updated_at=contract.updated_at
    )


@router.get("/{draft_id}/export")
async def export_contract(
    draft_id: int,
    format: str = "pdf",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    导出合同
    支持格式: pdf (默认)
    """
    from fastapi.responses import Response
    from urllib.parse import quote

    contract = db.query(Contract).filter(
        Contract.id == draft_id,
        Contract.user_id == current_user.id
    ).first()

    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    # 获取合同内容
    if contract.status == "completed" and contract.content:
        content = contract.content
    else:
        content = await _render_contract(db, contract)

    filename = contract.title or contract.contract_no
    # URL编码文件名以支持中文
    encoded_filename = quote(f"{filename}.pdf")

    if format == "pdf":
        # PDF导出
        pdf_content = await _generate_pdf(content, contract.contract_no)
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    else:
        # 其他格式暂不支持
        raise HTTPException(
            status_code=400,
            detail="目前仅支持PDF格式导出"
        )


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
        session_id=draft.session_id,
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

    # 获取字段定义，用于将name映射到label
    fields_definition = await _get_fields_definition(db, draft.contract_type)
    name_to_label = {f['name']: f.get('label', f['name']) for f in fields_definition}

    if template and template.content:
        # 使用模板渲染
        content = template.content
        for key, value in field_values.items():
            content = content.replace(f"{{{{{key}}}}}", str(value) if value else "")
            content = content.replace(f"【{key}】", str(value) if value else "")
            # 也尝试用中文标签替换
            label = name_to_label.get(key, key)
            content = content.replace(f"【{label}】", str(value) if value else "")
        return content

    # 无模板，生成标准格式（使用中文标签）
    # 合同类型中文名
    contract_type_name = draft.contract_type
    for f in fields_definition:
        if f.get('name') == 'contract_type':
            continue

    lines = [
        f"# {draft.contract_type}",
        "",
        f"合同编号：{draft.contract_no}",
        "",
        "---",
        ""
    ]

    # 按字段定义的顺序显示
    for field in fields_definition:
        field_name = field.get('name')
        field_label = field.get('label', field_name)
        value = field_values.get(field_name, '')
        if value:
            lines.append(f"**{field_label}**：{value}")

    lines.extend([
        "",
        "---",
        "",
        "本合同一式两份，甲乙双方各执一份，具有同等法律效力。",
        "",
        f"签订日期：{datetime.now().strftime('%Y年%m月%d日')}"
    ])

    return "\n".join(lines)


async def _generate_pdf(content: str, contract_no: str) -> bytes:
    """生成正式PDF合同文档"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
    from reportlab.lib import colors
    import io
    import os
    import re

    # 注册中文字体 - 宋体用于正文，黑体用于标题
    font_paths = {
        'SimSun': [
            "C:/Windows/Fonts/simsun.ttc",
            "/System/Library/Fonts/Songti.ttc",
            "/usr/share/fonts/truetype/arphic/uming.ttc",
        ],
        'SimHei': [
            "C:/Windows/Fonts/simhei.ttf",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        ]
    }

    body_font = 'SimSun'
    title_font = 'SimHei'

    # 尝试注册字体
    for font_name, paths in font_paths.items():
        for font_path in paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    break
                except:
                    continue

    # 验证字体是否可用
    try:
        pdfmetrics.getFont(body_font)
    except:
        body_font = 'Helvetica'
        title_font = 'Helvetica'

    # 创建PDF - 使用更正式的边距
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2.5*cm,
        leftMargin=2.5*cm,
        topMargin=2.5*cm,
        bottomMargin=2*cm
    )

    # 定义正式文档样式
    styles = getSampleStyleSheet()

    # 合同标题样式 - 大号黑体，居中
    contract_title_style = ParagraphStyle(
        'ContractTitle',
        fontName=title_font,
        fontSize=22,
        leading=30,
        alignment=TA_CENTER,
        spaceAfter=8,
        spaceBefore=20,
        textColor=colors.black,
    )

    # 合同编号样式 - 小号字体，居中
    contract_no_style = ParagraphStyle(
        'ContractNo',
        fontName=body_font,
        fontSize=11,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=25,
        textColor=colors.HexColor('#666666'),
    )

    # 条款标题样式 - 黑体加粗
    section_style = ParagraphStyle(
        'Section',
        fontName=title_font,
        fontSize=14,
        leading=22,
        spaceBefore=18,
        spaceAfter=8,
        textColor=colors.black,
    )

    # 正文样式 - 宋体，两端对齐，首行缩进
    body_style = ParagraphStyle(
        'Body',
        fontName=body_font,
        fontSize=12,
        leading=22,
        alignment=TA_JUSTIFY,
        firstLineIndent=24,  # 首行缩进2字符
        spaceAfter=6,
    )

    # 正文无缩进样式
    body_no_indent_style = ParagraphStyle(
        'BodyNoIndent',
        fontName=body_font,
        fontSize=12,
        leading=22,
        alignment=TA_LEFT,
        spaceAfter=6,
    )

    # 子条款样式 - 带编号缩进
    sub_item_style = ParagraphStyle(
        'SubItem',
        fontName=body_font,
        fontSize=12,
        leading=22,
        leftIndent=24,
        spaceAfter=4,
    )

    # 甲乙方信息样式
    party_style = ParagraphStyle(
        'Party',
        fontName=body_font,
        fontSize=12,
        leading=22,
        spaceAfter=4,
    )

    # 分隔线样式
    separator_style = ParagraphStyle(
        'Separator',
        fontName=body_font,
        fontSize=12,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=4,
    )

    # 签字区域样式
    signature_style = ParagraphStyle(
        'Signature',
        fontName=body_font,
        fontSize=12,
        leading=22,
        alignment=TA_LEFT,
        spaceAfter=4,
    )

    # 页脚样式
    footer_style = ParagraphStyle(
        'Footer',
        fontName=body_font,
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#999999'),
    )

    # 处理内容
    normalized_content = content.replace('\\n', '\n')
    lines = normalized_content.split('\n')

    story = []
    is_first_title = True
    title_added = False  # 跟踪是否已添加合同标题

    # 转义XML特殊字符
    def escape_xml(text):
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # 检测是否是合同标题行
    def is_contract_title(line):
        # 包含"合同"且长度较短（通常是标题）
        if '合同' in line and len(line) < 20:
            # 排除条款标题（以一、二、三开头）
            if not re.match(r'^[一二三四五六七八九十]+、', line):
                # 排除正文描述
                if not line.startswith('根据') and '双方' not in line:
                    return True
        return False

    for line in lines:
        original_line = line
        line = line.strip()

        if not line:
            continue

        # 判断内容类型
        # 1. Markdown标题 # 标题
        if line.startswith('# '):
            text = line[2:].strip()
            if is_first_title:
                # 第一个标题作为合同标题
                story.append(Paragraph(text, contract_title_style))
                story.append(Paragraph(f"合同编号：{contract_no}", contract_no_style))
                is_first_title = False
                title_added = True
            else:
                story.append(Paragraph(text, section_style))

        # 2. 自动识别合同标题（第一行或包含"合同"的短行）
        elif is_first_title and is_contract_title(line):
            story.append(Paragraph(escape_xml(line), contract_title_style))
            story.append(Paragraph(f"合同编号：{contract_no}", contract_no_style))
            is_first_title = False
            title_added = True

        # 3. 分隔线
        elif line == '---':
            story.append(Spacer(1, 0.3*cm))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CCCCCC')))
            story.append(Spacer(1, 0.3*cm))

        # 4. 条款标题 (一、二、三...开头)
        elif re.match(r'^[一二三四五六七八九十]+、', line):
            story.append(Paragraph(escape_xml(line), section_style))

        # 5. 编号列表 (1. 2. 3. 开头)
        elif re.match(r'^\d+\.', line):
            story.append(Paragraph(escape_xml(line), sub_item_style))

        # 6. 粗体文本 **text**
        elif line.startswith('**') and line.endswith('**'):
            text = line[2:-2]
            story.append(Paragraph(f"<b>{escape_xml(text)}</b>", body_no_indent_style))

        # 7. 甲乙方信息行
        elif '（甲方）' in line or '（乙方）' in line or '甲方：' in line or '乙方：' in line:
            story.append(Paragraph(escape_xml(line), party_style))

        # 8. 签字相关行
        elif '签字' in line or '盖章' in line or '日期：' in line or '年' in line and '月' in line and '日' in line:
            story.append(Spacer(1, 0.2*cm))
            story.append(Paragraph(escape_xml(line), signature_style))

        # 9. 合同编号行 (跳过，已经在标题下方显示)
        elif '合同编号' in line:
            continue

        # 10. 普通段落
        else:
            story.append(Paragraph(escape_xml(line), body_style))

    # 添加签字区域
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CCCCCC')))
    story.append(Spacer(1, 0.5*cm))

    # 签字栏
    story.append(Paragraph("甲方（签章）：____________________", signature_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("乙方（签章）：____________________", signature_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("签订日期：______年______月______日", signature_style))

    # 添加页脚
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CCCCCC')))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"本合同一式两份，甲乙双方各执一份，具有同等法律效力。", footer_style))

    doc.build(story)
    return buffer.getvalue()
