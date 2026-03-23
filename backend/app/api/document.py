"""
文档管理 API 路由
"""
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.models.document import Document, Template, FieldDefinition, DocumentType
from app.models.config import EmbeddingConfig
from app.schemas.document import (
    DocumentCreate, DocumentResponse, DocumentListResponse,
    TemplateCreate, TemplateUpdate, TemplateResponse,
    FieldDefinitionCreate, FieldDefinitionUpdate, FieldDefinitionResponse,
    ContractField
)
from app.services.rag_service import RAGService
from app.utils.security import get_current_admin
from app.config import settings

router = APIRouter(prefix="/api/admin/documents", tags=["文档管理"])


# ==================== 文档上传/管理 ====================

@router.get("", response_model=DocumentListResponse)
async def list_documents(
    doc_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """获取文档列表"""
    query = db.query(Document)

    if doc_type:
        query = query.filter(Document.doc_type == doc_type)

    total = query.count()
    items = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()

    return DocumentListResponse(total=total, items=items)


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form(default="other"),
    name: Optional[str] = Form(default=None),
    description: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """上传文档"""
    # 验证文件类型
    allowed_types = ["pdf", "docx", "doc", "md", "txt"]
    file_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file_ext}，支持: {', '.join(allowed_types)}"
        )

    # 生成存储路径
    doc_id = str(uuid.uuid4())[:8]
    file_name = f"{doc_id}_{file.filename}"
    file_path = os.path.join(settings.DOCUMENTS_DIR, file_name)

    # 保存文件
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # 创建数据库记录
    document = Document(
        name=name or file.filename,
        file_path=file_path,
        file_type=file_ext,
        doc_type=doc_type,
        description=description,
        content="",  # 待解析
        is_indexed=False
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return document


@router.post("/{doc_id}/index")
async def index_document(
    doc_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """将文档索引到向量库"""
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    if not document.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文档内容为空，请先解析"
        )

    # 添加到向量库
    chunk_count = await RAGService.add_text(
        document.content,
        metadata={
            "doc_id": document.id,
            "doc_name": document.name,
            "doc_type": document.doc_type
        },
        db=db
    )

    # 更新状态
    document.is_indexed = True
    document.chunk_count = chunk_count
    db.commit()

    return {"message": "索引成功", "chunk_count": chunk_count}


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """删除文档"""
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除文件
    if os.path.exists(document.file_path):
        os.remove(document.file_path)

    # 从向量库删除（如果已索引）
    if document.is_indexed:
        await RAGService.delete_by_metadata({"doc_id": doc_id}, db)

    # 删除数据库记录
    db.delete(document)
    db.commit()

    return {"message": "删除成功"}


# ==================== 合同模板管理 ====================

@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    contract_type: Optional[str] = None,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """获取模板列表"""
    query = db.query(Template).filter(Template.is_active == True)

    if contract_type:
        query = query.filter(Template.contract_type == contract_type)

    return query.order_by(Template.created_at.desc()).all()


@router.post("/templates/upload", response_model=TemplateResponse)
async def upload_template(
    file: UploadFile = File(...),
    name: str = Form(...),
    contract_type: str = Form(...),
    description: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """上传合同模板"""
    # 验证文件类型
    allowed_types = ["pdf", "docx", "doc", "md", "txt"]
    file_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file_ext}"
        )

    # 生成存储路径
    template_id = str(uuid.uuid4())[:8]
    file_name = f"template_{template_id}_{file.filename}"
    file_path = os.path.join(settings.TEMPLATES_DIR, file_name)

    # 保存文件
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # 创建数据库记录
    template = Template(
        name=name,
        contract_type=contract_type,
        file_path=file_path,
        file_type=file_ext,
        description=description
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    return template


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """获取模板详情"""
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template


@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    data: TemplateUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """更新模板"""
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)

    db.commit()
    db.refresh(template)
    return template


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """删除模板"""
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    # 删除文件
    if os.path.exists(template.file_path):
        os.remove(template.file_path)

    db.delete(template)
    db.commit()

    return {"message": "删除成功"}


# ==================== 字段定义管理 ====================

@router.get("/field-definitions", response_model=List[FieldDefinitionResponse])
async def list_field_definitions(
    contract_type: Optional[str] = None,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """获取字段定义列表"""
    query = db.query(FieldDefinition).filter(FieldDefinition.is_active == True)

    if contract_type:
        query = query.filter(FieldDefinition.contract_type == contract_type)

    return query.order_by(FieldDefinition.created_at.desc()).all()


@router.post("/field-definitions", response_model=FieldDefinitionResponse)
async def create_field_definition(
    data: FieldDefinitionCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """创建字段定义"""
    # 验证 JSON 格式
    import json
    try:
        json.loads(data.fields)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fields 必须是有效的 JSON 格式"
        )

    field_def = FieldDefinition(**data.model_dump())
    db.add(field_def)
    db.commit()
    db.refresh(field_def)
    return field_def


@router.get("/field-definitions/{def_id}", response_model=FieldDefinitionResponse)
async def get_field_definition(
    def_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """获取字段定义详情"""
    field_def = db.query(FieldDefinition).filter(FieldDefinition.id == def_id).first()
    if not field_def:
        raise HTTPException(status_code=404, detail="字段定义不存在")
    return field_def


@router.put("/field-definitions/{def_id}", response_model=FieldDefinitionResponse)
async def update_field_definition(
    def_id: int,
    data: FieldDefinitionUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """更新字段定义"""
    field_def = db.query(FieldDefinition).filter(FieldDefinition.id == def_id).first()
    if not field_def:
        raise HTTPException(status_code=404, detail="字段定义不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 验证 JSON 格式
    if "fields" in update_data:
        import json
        try:
            json.loads(update_data["fields"])
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fields 必须是有效的 JSON 格式"
            )

    for key, value in update_data.items():
        setattr(field_def, key, value)

    db.commit()
    db.refresh(field_def)
    return field_def


@router.delete("/field-definitions/{def_id}")
async def delete_field_definition(
    def_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """删除字段定义"""
    field_def = db.query(FieldDefinition).filter(FieldDefinition.id == def_id).first()
    if not field_def:
        raise HTTPException(status_code=404, detail="字段定义不存在")

    db.delete(field_def)
    db.commit()

    return {"message": "删除成功"}


# ==================== 预置租赁合同字段定义 ====================

LEASE_CONTRACT_FIELDS = '''
[
  {
    "name": "lessor_name",
    "label": "出租方姓名",
    "type": "text",
    "required": true,
    "placeholder": "请输入出租方姓名",
    "order": 1
  },
  {
    "name": "lessor_id",
    "label": "出租方身份证号",
    "type": "text",
    "required": true,
    "placeholder": "请输入出租方身份证号",
    "order": 2
  },
  {
    "name": "lessee_name",
    "label": "承租方姓名",
    "type": "text",
    "required": true,
    "placeholder": "请输入承租方姓名",
    "order": 3
  },
  {
    "name": "lessee_id",
    "label": "承租方身份证号",
    "type": "text",
    "required": true,
    "placeholder": "请输入承租方身份证号",
    "order": 4
  },
  {
    "name": "property_address",
    "label": "房屋地址",
    "type": "text",
    "required": true,
    "placeholder": "请输入房屋详细地址",
    "order": 5
  },
  {
    "name": "property_area",
    "label": "建筑面积(平方米)",
    "type": "number",
    "required": true,
    "placeholder": "请输入建筑面积",
    "order": 6
  },
  {
    "name": "rent_amount",
    "label": "月租金(元)",
    "type": "number",
    "required": true,
    "placeholder": "请输入月租金",
    "order": 7
  },
  {
    "name": "deposit_amount",
    "label": "押金(元)",
    "type": "number",
    "required": true,
    "placeholder": "请输入押金金额",
    "order": 8
  },
  {
    "name": "lease_start",
    "label": "租赁开始日期",
    "type": "date",
    "required": true,
    "placeholder": "请选择开始日期",
    "order": 9
  },
  {
    "name": "lease_end",
    "label": "租赁结束日期",
    "type": "date",
    "required": true,
    "placeholder": "请选择结束日期",
    "order": 10
  },
  {
    "name": "payment_method",
    "label": "付款方式",
    "type": "select",
    "required": true,
    "options": ["月付", "季付", "半年付", "年付"],
    "default": "季付",
    "order": 11
  },
  {
    "name": "payment_day",
    "label": "付款日期(每月几号)",
    "type": "number",
    "required": true,
    "placeholder": "例如: 5",
    "order": 12
  },
  {
    "name": "purpose",
    "label": "租赁用途",
    "type": "select",
    "required": true,
    "options": ["居住", "办公", "商业经营"],
    "default": "居住",
    "order": 13
  },
  {
    "name": "contact_phone",
    "label": "联系电话",
    "type": "text",
    "required": true,
    "placeholder": "请输入联系电话",
    "order": 14
  },
  {
    "name": "remarks",
    "label": "备注",
    "type": "textarea",
    "required": false,
    "placeholder": "其他约定事项",
    "order": 15
  }
]
'''


@router.post("/field-definitions/init-lease")
async def init_lease_field_definition(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """初始化租赁合同字段定义"""
    # 检查是否已存在
    existing = db.query(FieldDefinition).filter(
        FieldDefinition.contract_type == "租赁合同"
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="租赁合同字段定义已存在"
        )

    field_def = FieldDefinition(
        name="租赁合同字段定义",
        contract_type="租赁合同",
        fields=LEASE_CONTRACT_FIELDS
    )
    db.add(field_def)
    db.commit()
    db.refresh(field_def)

    return {"message": "初始化成功", "id": field_def.id}
