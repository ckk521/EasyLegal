"""
合同审核 API 路由

包含：
- 合同列表（筛选、搜索）
- 合同详情
- AI审核
- 人工审核流程
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_db
from app.models.document import Contract
from app.models.user import User
from app.models.staff import Staff
from app.schemas.contract_review import (
    ContractListResponse,
    ContractListItem,
    ContractDetail,
    MessageResponse,
    SubmitReviewRequest,
    AssignReviewerRequest,
    StartReviewRequest,
    FirstReviewPassRequest,
    FinalReviewRequest,
    EditContentRequest,
    DirectCompleteRequest,
    ReviewActionResult,
    ReviewLogItem,
    ReviewLogResponse
)
from app.utils.security import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["合同审核"])


# ==================== 合同列表 ====================

@router.get("/contracts", response_model=ContractListResponse)
async def list_contracts(
    status: Optional[str] = Query(None, description="合同状态筛选"),
    contract_type: Optional[str] = Query(None, description="合同类型筛选"),
    user_id: Optional[int] = Query(None, description="用户ID筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索（合同编号、用户名）"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取合同列表（支持筛选、搜索）

    - admin可查看所有合同
    - 支持按状态、类型、用户、时间筛选
    - 支持关键词搜索
    """
    query = db.query(Contract).join(User, Contract.user_id == User.id, isouter=True)

    # 状态筛选
    if status:
        query = query.filter(Contract.status == status)

    # 类型筛选
    if contract_type:
        query = query.filter(Contract.contract_type == contract_type)

    # 用户筛选
    if user_id:
        query = query.filter(Contract.user_id == user_id)

    # 时间范围筛选
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Contract.updated_at >= start_dt)
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            # 包含当天，所以加一天
            from datetime import timedelta
            end_dt = end_dt + timedelta(days=1)
            query = query.filter(Contract.updated_at < end_dt)
        except ValueError:
            pass

    # 关键词搜索
    if keyword:
        keyword_filter = f"%{keyword}%"
        query = query.filter(
            (Contract.contract_no.ilike(keyword_filter)) |
            (Contract.title.ilike(keyword_filter)) |
            (User.username.ilike(keyword_filter)) |
            (User.nickname.ilike(keyword_filter))
        )

    # 统计总数
    total = query.count()

    # 排序和分页
    contracts = query.order_by(Contract.updated_at.desc()).offset(skip).limit(limit).all()

    # 构建响应
    items = []
    for c in contracts:
        # 获取用户名
        user = db.query(User).filter(User.id == c.user_id).first()
        user_name = user.nickname or user.username if user else None

        # 获取审核人名
        reviewer_name = None
        if c.assigned_reviewer_id:
            reviewer = db.query(Staff).filter(Staff.id == c.assigned_reviewer_id).first()
            reviewer_name = reviewer.nickname or reviewer.username if reviewer else None

        items.append(ContractListItem(
            id=c.id,
            contract_no=c.contract_no,
            title=c.title,
            contract_type=c.contract_type,
            status=c.status,
            user_id=c.user_id,
            user_name=user_name,
            assigned_reviewer_id=c.assigned_reviewer_id,
            assigned_reviewer_name=reviewer_name,
            created_at=c.created_at,
            updated_at=c.updated_at
        ))

    return ContractListResponse(total=total, items=items)


@router.get("/contracts/{contract_id}", response_model=ContractDetail)
async def get_contract_detail(
    contract_id: int,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取合同详情

    - 包含合同基本信息和审核信息
    """
    import json

    def get_staff_name(staff_id: int) -> Optional[str]:
        if not staff_id:
            return None
        staff = db.query(Staff).filter(Staff.id == staff_id).first()
        return staff.nickname or staff.username if staff else None

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="合同不存在"
        )

    # 获取用户名
    user = db.query(User).filter(User.id == contract.user_id).first()
    user_name = user.nickname or user.username if user else None

    # 解析字段值
    field_values = {}
    if contract.field_values:
        try:
            field_values = json.loads(contract.field_values)
        except:
            pass

    return ContractDetail(
        id=contract.id,
        contract_no=contract.contract_no,
        title=contract.title,
        contract_type=contract.contract_type,
        status=contract.status,
        user_id=contract.user_id,
        user_name=user_name,
        template_id=contract.template_id,
        field_values=field_values,
        content=contract.content,
        # 审核分配
        assigned_reviewer_id=contract.assigned_reviewer_id,
        assigned_reviewer_name=get_staff_name(contract.assigned_reviewer_id),
        # 初审
        first_reviewed_by=contract.first_reviewed_by,
        first_reviewed_by_name=get_staff_name(contract.first_reviewed_by),
        first_reviewed_at=contract.first_reviewed_at,
        first_review_comment=contract.first_review_comment,
        # 终审
        final_reviewed_by=contract.final_reviewed_by,
        final_reviewed_by_name=get_staff_name(contract.final_reviewed_by),
        final_reviewed_at=contract.final_reviewed_at,
        final_review_comment=contract.final_review_comment,
        # 驳回
        rejected_by=contract.rejected_by,
        rejected_by_name=get_staff_name(contract.rejected_by),
        rejected_at=contract.rejected_at,
        reject_reason=contract.reject_reason,
        # 合同编辑
        content_edited=contract.content_edited,
        content_edited_by=contract.content_edited_by,
        content_edited_by_name=get_staff_name(contract.content_edited_by),
        content_edited_at=contract.content_edited_at,
        # 兼容旧字段
        reviewed_by=contract.reviewed_by,
        reviewed_by_name=get_staff_name(contract.reviewed_by),
        reviewed_at=contract.reviewed_at,
        created_at=contract.created_at,
        updated_at=contract.updated_at
    )


# ==================== 合同类型列表 ====================

@router.get("/contract-types")
async def get_contract_types(
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取所有合同类型（用于筛选下拉框）"""
    from sqlalchemy import distinct

    types = db.query(distinct(Contract.contract_type)).all()
    return [{"value": t[0], "label": t[0]} for t in types if t[0]]


# ==================== 合同状态列表 ====================

@router.get("/contract-statuses")
async def get_contract_statuses():
    """获取所有合同状态（用于筛选下拉框）"""
    return [
        {"value": "draft", "label": "草稿"},
        {"value": "pending_review", "label": "待审核"},
        {"value": "ai_reviewed", "label": "AI已初审"},
        {"value": "in_review", "label": "审核中"},
        {"value": "pending_manager", "label": "等待终审"},
        {"value": "rejected", "label": "已驳回"},
        {"value": "completed", "label": "已完成"},
    ]


# ==================== 审核流程 ====================

def _log_action(
    db: Session,
    contract_id: int,
    action: str,
    operator_id: int,
    operator_role: str,
    detail: dict = None
):
    """记录审核日志"""
    from app.models.document import ContractReviewLog
    import json

    log = ContractReviewLog(
        contract_id=contract_id,
        action=action,
        operator_id=operator_id,
        operator_role=operator_role,
        detail=json.dumps(detail, ensure_ascii=False) if detail else None
    )
    db.add(log)
    db.commit()


def _get_operator_name(db: Session, staff_id: int) -> str:
    """获取操作人名称"""
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    return staff.nickname or staff.username if staff else f"用户{staff_id}"


@router.post("/contracts/{contract_id}/submit-review", response_model=ReviewActionResult)
async def submit_review(
    contract_id: int,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    提交审核

    - 状态变更: draft → pending_review
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="合同不存在")

    if contract.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"合同状态为{contract.status}，无法提交审核")

    contract.status = "pending_review"
    contract.updated_at = datetime.now()
    db.commit()

    # 记录日志
    _log_action(db, contract_id, "submit_review", current_admin.id, "admin")

    return ReviewActionResult(
        message="已提交审核",
        contract_id=contract_id,
        status=contract.status,
        signed_by=_get_operator_name(db, current_admin.id),
        signed_at=datetime.now()
    )


@router.post("/contracts/{contract_id}/assign", response_model=ReviewActionResult)
async def assign_reviewer(
    contract_id: int,
    request: AssignReviewerRequest,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    分配审核人

    - 可在 pending_review 或 ai_reviewed 状态下分配
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="合同不存在")

    if contract.status not in ["pending_review", "ai_reviewed"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前状态无法分配审核人")

    # 验证审核人存在
    reviewer = db.query(Staff).filter(Staff.id == request.reviewer_id).first()
    if not reviewer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审核人不存在")

    contract.assigned_reviewer_id = request.reviewer_id
    contract.status = "in_review"
    contract.updated_at = datetime.now()
    db.commit()

    # 记录日志
    _log_action(db, contract_id, "assign_reviewer", current_admin.id, "admin", {
        "reviewer_id": request.reviewer_id,
        "reviewer_name": reviewer.nickname or reviewer.username
    })

    return ReviewActionResult(
        message="已分配审核人",
        contract_id=contract_id,
        status=contract.status,
        signed_by=_get_operator_name(db, current_admin.id),
        signed_at=datetime.now()
    )


@router.post("/contracts/{contract_id}/start-review", response_model=ReviewActionResult)
async def start_review(
    contract_id: int,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    开始审核

    - 状态变更: pending_review/ai_reviewed → in_review
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="合同不存在")

    if contract.status not in ["pending_review", "ai_reviewed"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前状态无法开始审核")

    contract.status = "in_review"
    contract.assigned_reviewer_id = current_admin.id  # admin自己审核
    contract.updated_at = datetime.now()
    db.commit()

    _log_action(db, contract_id, "start_review", current_admin.id, "admin")

    return ReviewActionResult(
        message="已开始审核",
        contract_id=contract_id,
        status=contract.status,
        signed_by=_get_operator_name(db, current_admin.id),
        signed_at=datetime.now()
    )


@router.post("/contracts/{contract_id}/first-review-pass", response_model=ReviewActionResult)
async def first_review_pass(
    contract_id: int,
    request: FirstReviewPassRequest,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    初审通过

    - 状态变更: in_review → pending_manager
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="合同不存在")

    if contract.status != "in_review":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前状态无法进行初审")

    contract.status = "pending_manager"
    contract.first_reviewed_by = current_admin.id
    contract.first_reviewed_at = datetime.now()
    contract.first_review_comment = request.comment
    contract.updated_at = datetime.now()
    db.commit()

    _log_action(db, contract_id, "first_review_pass", current_admin.id, "admin", {
        "comment": request.comment
    })

    return ReviewActionResult(
        message="初审通过，已提交终审",
        contract_id=contract_id,
        status=contract.status,
        signed_by=_get_operator_name(db, current_admin.id),
        signed_at=datetime.now()
    )


@router.post("/contracts/{contract_id}/final-review", response_model=ReviewActionResult)
async def final_review(
    contract_id: int,
    request: FinalReviewRequest,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    终审（通过/驳回）

    - 通过: pending_manager → completed
    - 驳回: pending_manager → rejected
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="合同不存在")

    if contract.status != "pending_manager":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前状态无法进行终审")

    if request.action not in ["pass", "reject"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="操作类型无效，请使用 pass 或 reject")

    if request.action == "reject" and not request.reject_reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="驳回时必须填写驳回原因")

    now = datetime.now()
    operator_name = _get_operator_name(db, current_admin.id)

    if request.action == "pass":
        contract.status = "completed"
        contract.final_reviewed_by = current_admin.id
        contract.final_reviewed_at = now
        contract.final_review_comment = request.comment
        contract.reviewed_by = current_admin.id
        contract.reviewed_at = now
        message = "终审通过，合同已完成"
    else:
        contract.status = "rejected"
        contract.rejected_by = current_admin.id
        contract.rejected_at = now
        contract.reject_reason = request.reject_reason
        message = "已驳回合同"

    contract.updated_at = now
    db.commit()

    _log_action(db, contract_id, f"final_review_{request.action}", current_admin.id, "admin", {
        "comment": request.comment,
        "reject_reason": request.reject_reason
    })

    return ReviewActionResult(
        message=message,
        contract_id=contract_id,
        status=contract.status,
        signed_by=operator_name,
        signed_at=now
    )


@router.post("/contracts/{contract_id}/direct-complete", response_model=ReviewActionResult)
async def direct_complete(
    contract_id: int,
    request: DirectCompleteRequest,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    admin直接完成审核

    - 任意状态 → completed
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="合同不存在")

    now = datetime.now()
    contract.status = "completed"
    contract.reviewed_by = current_admin.id
    contract.reviewed_at = now
    contract.final_reviewed_by = current_admin.id
    contract.final_reviewed_at = now
    contract.final_review_comment = request.comment
    contract.updated_at = now
    db.commit()

    _log_action(db, contract_id, "direct_complete", current_admin.id, "admin", {
        "comment": request.comment
    })

    return ReviewActionResult(
        message="审核完成",
        contract_id=contract_id,
        status=contract.status,
        signed_by=_get_operator_name(db, current_admin.id),
        signed_at=now
    )


@router.put("/contracts/{contract_id}/content", response_model=ReviewActionResult)
async def edit_contract_content(
    contract_id: int,
    request: EditContentRequest,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    编辑合同内容

    - 仅在审核流程中可编辑
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="合同不存在")

    if contract.status not in ["in_review", "pending_manager", "rejected", "ai_reviewed"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前状态无法编辑合同内容")

    now = datetime.now()
    contract.content_edited = request.content
    contract.content_edited_by = current_admin.id
    contract.content_edited_at = now
    contract.updated_at = now
    db.commit()

    _log_action(db, contract_id, "edit_content", current_admin.id, "admin")

    return ReviewActionResult(
        message="合同内容已修改",
        contract_id=contract_id,
        status=contract.status,
        signed_by=_get_operator_name(db, current_admin.id),
        signed_at=now
    )


@router.post("/contracts/{contract_id}/resubmit", response_model=ReviewActionResult)
async def resubmit_review(
    contract_id: int,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    重新提交审核（驳回后）

    - rejected → in_review
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="合同不存在")

    if contract.status != "rejected":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有已驳回的合同可以重新提交")

    contract.status = "in_review"
    # 保留AI报告，清除驳回信息
    contract.rejected_by = None
    contract.rejected_at = None
    contract.reject_reason = None
    contract.updated_at = datetime.now()
    db.commit()

    _log_action(db, contract_id, "resubmit_review", current_admin.id, "admin")

    return ReviewActionResult(
        message="已重新提交审核",
        contract_id=contract_id,
        status=contract.status,
        signed_by=_get_operator_name(db, current_admin.id),
        signed_at=datetime.now()
    )


# ==================== 审核日志 ====================

@router.get("/contracts/{contract_id}/logs", response_model=ReviewLogResponse)
async def get_review_logs(
    contract_id: int,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取合同审核日志"""
    from app.models.document import ContractReviewLog
    import json

    # 验证合同存在
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="合同不存在")

    logs = db.query(ContractReviewLog).filter(
        ContractReviewLog.contract_id == contract_id
    ).order_by(ContractReviewLog.created_at.desc()).all()

    items = []
    for log in logs:
        operator_name = _get_operator_name(db, log.operator_id)
        detail = None
        if log.detail:
            try:
                detail = json.loads(log.detail)
            except:
                pass

        items.append(ReviewLogItem(
            id=log.id,
            contract_id=log.contract_id,
            action=log.action,
            operator_id=log.operator_id,
            operator_name=operator_name,
            operator_role=log.operator_role,
            detail=detail,
            created_at=log.created_at
        ))

    return ReviewLogResponse(total=len(items), items=items)


# ==================== AI审核 ====================

@router.post("/contracts/{contract_id}/ai-review")
async def ai_review_contract(
    contract_id: int,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    执行AI审核（SSE流式返回进度）

    - 状态变更: pending_review → ai_reviewed
    - 生成AI审核报告
    - 实时返回审核进度
    """
    from fastapi.responses import StreamingResponse
    from app.models.document import ContractReviewReport
    from app.services.ai_review_service import get_ai_review_service
    import json as json_module

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="合同不存在")

    if contract.status not in ["pending_review", "in_review", "rejected", "ai_reviewed"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前状态无法进行AI审核")

    # 获取合同内容
    content = contract.content_edited or contract.content
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="合同内容为空，无法审核")

    # 预先获取需要的数据，避免在生成器中访问 db
    contract_type = contract.contract_type or "通用合同"
    admin_id = current_admin.id

    # 获取 AI 服务实例
    ai_service = get_ai_review_service(db)

    async def generate_progress():
        """SSE生成器：流式返回审核进度"""
        # 创建新的 db session 用于流式处理
        from app.database import SessionLocal
        stream_db = SessionLocal()

        try:
            final_result = None

            async for progress_data in ai_service.review_contract_stream(
                contract_content=content,
                contract_type=contract_type
            ):
                # 收集最终结果
                if progress_data.get("status") == "complete":
                    final_result = progress_data

                # 发送进度更新
                yield f"data: {json_module.dumps(progress_data, ensure_ascii=False)}\n\n"

            # 保存审核报告
            if final_result:
                report = ContractReviewReport(
                    contract_id=contract_id,
                    risk_summary=json_module.dumps(final_result.get("risk_summary", {}), ensure_ascii=False),
                    risk_items=json_module.dumps(final_result.get("risk_items", []), ensure_ascii=False),
                    ai_model="glm-5",
                    created_at=datetime.now()
                )
                stream_db.add(report)

                # 更新合同状态（只有 pending_review 状态才更新为 ai_reviewed）
                stream_contract = stream_db.query(Contract).filter(Contract.id == contract_id).first()
                if stream_contract:
                    new_status = stream_contract.status
                    if stream_contract.status == "pending_review":
                        new_status = "ai_reviewed"
                        stream_contract.status = new_status
                    stream_contract.updated_at = datetime.now()
                else:
                    new_status = "ai_reviewed"  # 默认值
                stream_db.commit()

                # 发送完成消息（包含报告ID和状态）
                complete_data = {
                    "status": "saved",
                    "progress": 100,
                    "contract_id": contract_id,
                    "new_status": new_status,
                    "report": {
                        "id": report.id,
                        "risk_summary": final_result.get("risk_summary", {}),
                        "risk_items": final_result.get("risk_items", []),
                        "created_at": report.created_at.isoformat()
                    }
                }
                yield f"data: {json_module.dumps(complete_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_data = {
                "status": "error",
                "message": f"AI审核失败: {str(e)}"
            }
            yield f"data: {json_module.dumps(error_data, ensure_ascii=False)}\n\n"
        finally:
            stream_db.close()

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/contracts/{contract_id}/review-report")
async def get_review_report(
    contract_id: int,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取AI审核报告"""
    from app.models.document import ContractReviewReport
    import json as json_module

    # 验证合同存在
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="合同不存在")

    # 获取最新的审核报告
    report = db.query(ContractReviewReport).filter(
        ContractReviewReport.contract_id == contract_id
    ).order_by(ContractReviewReport.created_at.desc()).first()

    if not report:
        return {
            "message": "暂无审核报告",
            "contract_id": contract_id,
            "report": None
        }

    return {
        "message": "获取成功",
        "contract_id": contract_id,
        "report": {
            "id": report.id,
            "risk_summary": json_module.loads(report.risk_summary) if report.risk_summary else {},
            "risk_items": json_module.loads(report.risk_items) if report.risk_items else [],
            "ai_model": report.ai_model,
            "created_at": report.created_at.isoformat()
        }
    }


class ApplySuggestionRequest(BaseModel):
    """应用建议请求"""
    item_id: str


@router.post("/contracts/{contract_id}/apply-suggestion")
async def apply_suggestion(
    contract_id: int,
    request: ApplySuggestionRequest,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    标记审核建议为已采纳

    更新审核报告中对应建议的 applied 状态
    """
    from app.models.document import ContractReviewReport
    import json as json_module

    # 获取最新的审核报告
    report = db.query(ContractReviewReport).filter(
        ContractReviewReport.contract_id == contract_id
    ).order_by(ContractReviewReport.created_at.desc()).first()

    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审核报告不存在")

    # 解析并更新 risk_items
    risk_items = json_module.loads(report.risk_items) if report.risk_items else []

    updated = False
    for item in risk_items:
        if item.get("id") == request.item_id:
            item["applied"] = True
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该建议")

    # 保存更新
    report.risk_items = json_module.dumps(risk_items, ensure_ascii=False)
    db.commit()

    return {
        "message": "已标记为已采纳",
        "item_id": request.item_id
    }


class FormatContractRequest(BaseModel):
    """格式化合同请求"""
    pass


@router.post("/contracts/{contract_id}/format")
async def format_contract(
    contract_id: int,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    格式化合同内容

    调用AI整理合同格式，提高可读性
    """
    from app.services.ai_review_service import get_ai_review_service

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="合同不存在")

    # 获取合同内容（优先使用编辑后的内容）
    content = contract.content_edited or contract.content
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="合同内容为空")

    # 获取AI服务
    ai_service = get_ai_review_service(db)

    # 调用格式化服务
    result = await ai_service.format_contract(
        contract_content=content,
        contract_type=contract.contract_type or "通用合同"
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "格式化失败")
        )

    return {
        "message": "格式化完成",
        "contract_id": contract_id,
        "original_content": result.get("original_content"),
        "formatted_content": result.get("formatted_content")
    }


@router.post("/contracts/{contract_id}/apply-format")
async def apply_format(
    contract_id: int,
    request: EditContentRequest,
    current_admin: Staff = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    应用格式化后的内容

    将格式化后的内容保存到 content_edited
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="合同不存在")

    now = datetime.now()
    contract.content_edited = request.content
    contract.content_edited_by = current_admin.id
    contract.content_edited_at = now
    contract.updated_at = now
    db.commit()

    _log_action(db, contract_id, "apply_format", current_admin.id, "admin")

    return {
        "message": "已应用格式化内容",
        "contract_id": contract_id
    }