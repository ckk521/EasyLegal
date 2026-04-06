"""
合同审核模块 Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==================== 合同列表 ====================

class ContractListItem(BaseModel):
    """合同列表项"""
    id: int
    contract_no: str = Field(..., description="合同编号")
    title: Optional[str] = Field(None, description="合同标题")
    contract_type: str = Field(..., description="合同类型")
    status: str = Field(..., description="合同状态")
    user_id: int = Field(..., description="用户ID")
    user_name: Optional[str] = Field(None, description="用户名称")
    assigned_reviewer_id: Optional[int] = Field(None, description="分配的审核人ID")
    assigned_reviewer_name: Optional[str] = Field(None, description="审核人名称")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class ContractListResponse(BaseModel):
    """合同列表响应"""
    total: int = Field(..., description="总数")
    items: List[ContractListItem] = Field(..., description="合同列表")


# ==================== 合同详情 ====================

class ContractDetail(BaseModel):
    """合同详情"""
    id: int
    contract_no: str
    title: Optional[str]
    contract_type: str
    status: str
    user_id: int
    user_name: Optional[str]
    template_id: Optional[int]
    field_values: dict = Field(default_factory=dict)
    content: Optional[str] = None
    # 审核分配
    assigned_reviewer_id: Optional[int] = None
    assigned_reviewer_name: Optional[str] = None
    # 初审
    first_reviewed_by: Optional[int] = None
    first_reviewed_by_name: Optional[str] = None
    first_reviewed_at: Optional[datetime] = None
    first_review_comment: Optional[str] = None
    # 终审
    final_reviewed_by: Optional[int] = None
    final_reviewed_by_name: Optional[str] = None
    final_reviewed_at: Optional[datetime] = None
    final_review_comment: Optional[str] = None
    # 驳回
    rejected_by: Optional[int] = None
    rejected_by_name: Optional[str] = None
    rejected_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    # 合同编辑
    content_edited: Optional[str] = None
    content_edited_by: Optional[int] = None
    content_edited_by_name: Optional[str] = None
    content_edited_at: Optional[datetime] = None
    # 兼容旧字段
    reviewed_by: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== AI审核报告 ====================

class RiskItem(BaseModel):
    """风险项"""
    id: int
    level: str = Field(..., description="风险等级: high/medium/low")
    type: str = Field(..., description="风险类型: risk_clause/missing_clause/amount_error/format")
    title: str = Field(..., description="风险标题")
    content: str = Field(..., description="相关条款内容")
    reason: str = Field(..., description="风险原因")
    suggestion: str = Field(..., description="修改建议")
    status: str = Field(default="pending", description="状态: pending/confirmed/modified")


class RiskSummary(BaseModel):
    """风险摘要"""
    high: int = Field(default=0, description="高风险数量")
    medium: int = Field(default=0, description="中风险数量")
    low: int = Field(default=0, description="低风险数量")


class AIReviewReport(BaseModel):
    """AI审核报告"""
    id: int
    contract_id: int
    risk_summary: RiskSummary
    risk_items: List[RiskItem]
    ai_model: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== 审核操作 ====================

class AssignReviewerRequest(BaseModel):
    """分配审核人请求"""
    reviewer_id: int = Field(..., description="审核人ID")


class ConfirmItemRequest(BaseModel):
    """确认风险点请求"""
    item_id: int = Field(..., description="风险点ID")
    comment: Optional[str] = Field(None, description="审核意见")


class RejectContractRequest(BaseModel):
    """驳回合同请求"""
    reason: str = Field(..., description="驳回原因")


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str


# ==================== 审核流程 ====================

class SubmitReviewRequest(BaseModel):
    """提交审核请求"""
    pass


class AssignReviewerRequest(BaseModel):
    """分配审核人请求"""
    reviewer_id: int = Field(..., description="审核人ID")


class StartReviewRequest(BaseModel):
    """开始审核请求"""
    pass


class FirstReviewPassRequest(BaseModel):
    """初审通过请求"""
    comment: Optional[str] = Field(None, description="初审意见")


class FinalReviewRequest(BaseModel):
    """终审请求"""
    action: str = Field(..., description="操作: pass/reject")
    comment: Optional[str] = Field(None, description="终审意见")
    reject_reason: Optional[str] = Field(None, description="驳回原因（action=reject时必填）")


class EditContentRequest(BaseModel):
    """编辑合同内容请求"""
    content: str = Field(..., description="修改后的合同内容")


class DirectCompleteRequest(BaseModel):
    """admin直接完成请求"""
    comment: Optional[str] = Field(None, description="审核意见")


# ==================== 审核结果 ====================

class ReviewActionResult(BaseModel):
    """审核操作结果"""
    message: str
    contract_id: int
    status: str
    signed_by: str
    signed_at: datetime

    class Config:
        from_attributes = True


# ==================== 审核日志 ====================

class ReviewLogItem(BaseModel):
    """审核日志项"""
    id: int
    contract_id: int
    action: str
    operator_id: int
    operator_name: Optional[str] = None
    operator_role: Optional[str] = None
    detail: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewLogResponse(BaseModel):
    """审核日志响应"""
    total: int
    items: List[ReviewLogItem]
