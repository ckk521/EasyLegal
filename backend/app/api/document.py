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
    from app.services.document_service import DocumentParser

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
    file_content = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_content)

    # 解析文件内容
    parsed_content = ""
    try:
        parsed_content, _ = await DocumentParser.parse_file(file_path)
    except Exception as e:
        # 解析失败时使用空内容
        print(f"解析模板文件失败: {e}")

    # 创建数据库记录
    template = Template(
        name=name,
        contract_type=contract_type,
        file_path=file_path,
        file_type=file_ext,
        content=parsed_content,  # 存储解析后的内容
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


# 默认合同模板
DEFAULT_TEMPLATES = {
    "租赁合同": """# 房屋租赁合同

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

3.1 该房屋每月租金为人民币【月租金】元整。

3.2 押金为人民币【押金】元整，于签订本合同时一次性支付。

3.3 付款方式：【付款方式】。

## 第四条 房屋维护及维修

4.1 甲方应保证房屋及设施正常使用，发现问题及时维修。

4.2 乙方应合理使用房屋及其附属设施，不得擅自改变房屋结构或用途。

## 第五条 合同解除

5.1 有下列情形之一的，甲方可解除合同：
（1）乙方擅自将房屋转租、转让或转借他人的；
（2）乙方利用房屋进行非法活动，损害公共利益的；
（3）乙方拖欠租金累计达【违约天数】天的。

## 第六条 其他约定

【备注】

## 第七条 签署

本合同一式两份，甲、乙双方各执一份，自双方签字之日起生效。

甲方签字：__________________    日期：【签订日期】

乙方签字：__________________    日期：【签订日期】
""",
    "买卖合同": """# 房屋买卖合同

卖方（甲方）：【甲方名称】
身份证号码：【甲方身份证号】
联系电话：【甲方电话】

买方（乙方）：【乙方名称】
身份证号码：【乙方身份证号】
联系电话：【乙方电话】

根据《中华人民共和国民法典》及相关法律法规，甲乙双方在平等、自愿的基础上，就房屋买卖事宜达成如下协议：

## 第一条 房屋基本情况

1.1 房屋坐落：【房屋地址】

1.2 房屋建筑面积：【房屋面积】平方米

1.3 房屋所有权证号：【房产证号】

## 第二条 成交价格

2.1 该房屋成交价格为人民币【成交价格】元整。

2.2 付款方式：【付款方式】。

## 第三条 交房时间

甲方应于【交房日期】前将房屋交付给乙方。

## 第四条 产权过户

甲方应在本合同签订后【过户天数】日内，配合乙方办理房屋产权过户手续。

## 第五条 其他约定

【备注】

## 第六条 签署

本合同一式两份，甲、乙双方各执一份，自双方签字之日起生效。

甲方签字：__________________    日期：【签订日期】

乙方签字：__________________    日期：【签订日期】
""",
    "借款合同": """# 借款合同

出借人（甲方）：【甲方名称】
身份证号码：【甲方身份证号】
联系电话：【甲方电话】

借款人（乙方）：【乙方名称】
身份证号码：【乙方身份证号】
联系电话：【乙方电话】

根据《中华人民共和国民法典》及相关法律法规，甲乙双方在平等、自愿的基础上，就借款事宜达成如下协议：

## 第一条 借款金额

乙方因【借款用途】需要，向甲方借款人民币【借款金额】元整。

## 第二条 借款期限

借款期限自【借款开始日期】起至【借款结束日期】止。

## 第三条 利息

借款利息：【利息】（年利率/月利率）。

## 第四条 还款方式

还款方式：【还款方式】。

## 第五条 违约责任

乙方如未按期还款，应支付违约金人民币【违约金】元。

## 第六条 其他约定

【备注】

## 第七条 签署

本合同一式两份，甲、乙双方各执一份，自双方签字之日起生效。

甲方签字：__________________    日期：【签订日期】

乙方签字：__________________    日期：【签订日期】
""",

    # 通用合同模板 - 用于未匹配到具体类型的合同
    "通用合同": """# 合同

甲方：【甲方名称】
地址：【甲方地址】
联系人：【甲方联系人】
联系电话：【甲方电话】

乙方：【乙方名称】
地址：【乙方地址】
联系人：【乙方联系人】
联系电话：【乙方电话】

根据《中华人民共和国民法典》及相关法律法规的规定，甲、乙双方在平等、自愿的基础上，经友好协商，达成如下协议：

## 第一条 合同标的

【合同标的或主要内容描述】

## 第二条 合同金额及支付方式

2.1 合同总金额为人民币【合同金额】元整。

2.2 支付方式：【支付方式】。

2.3 支付时间：【支付时间】。

## 第三条 双方权利义务

3.1 甲方的权利和义务：
（1）【甲方权利义务1】
（2）【甲方权利义务2】

3.2 乙方的权利和义务：
（1）【乙方权利义务1】
（2）【乙方权利义务2】

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
}


@router.post("/templates/init-defaults")
async def init_default_templates(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """初始化默认合同模板到数据库"""
    created = []
    skipped = []

    for contract_type, content in DEFAULT_TEMPLATES.items():
        # 检查是否已存在
        existing = db.query(Template).filter(
            Template.contract_type == contract_type
        ).first()

        if existing:
            skipped.append(contract_type)
            continue

        # 创建模板记录（内容直接存储在数据库）
        template = Template(
            name=f"{contract_type}（默认模板）",
            contract_type=contract_type,
            file_path="",  # 默认模板不需要文件
            file_type="md",
            content=content,
            description=f"系统预置的{contract_type}模板，可直接在对话中使用"
        )
        db.add(template)
        created.append(contract_type)

    db.commit()

    return {
        "message": "初始化完成",
        "created": created,
        "skipped": skipped
    }

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
