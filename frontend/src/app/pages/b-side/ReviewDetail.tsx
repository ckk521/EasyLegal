import React, { useState, useEffect } from "react";
import {
  ChevronLeft,
  Save,
  Send,
  AlertCircle,
  CheckCircle,
  MessageSquare,
  Gavel,
  FileText,
  Edit3,
  Search,
  Maximize2,
  MoreVertical,
  Minus,
  Plus,
  RotateCcw,
  Check,
  Filter,
  Loader2,
  X,
  Sparkles,
  AlertTriangle,
  AlignLeft
} from "lucide-react";
import { useNavigate, useParams } from "react-router";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { motion, AnimatePresence } from "motion/react";
import { toast } from "sonner";
import {
  contractReviewApi,
  ContractReviewDetail,
  ReviewLogItem
} from "../../services/api";

function cn(...inputs: any[]) {
  return twMerge(clsx(inputs));
}

const statusMap: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'bg-slate-100 text-slate-600' },
  pending_review: { label: '待审核', color: 'bg-blue-50 text-blue-600' },
  ai_reviewed: { label: 'AI已初审', color: 'bg-cyan-50 text-cyan-600' },
  in_review: { label: '审核中', color: 'bg-amber-50 text-amber-600' },
  pending_manager: { label: '等待终审', color: 'bg-purple-50 text-purple-600' },
  rejected: { label: '已驳回', color: 'bg-rose-50 text-rose-600' },
  completed: { label: '已完成', color: 'bg-emerald-50 text-emerald-600' },
};

export function ReviewDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [contract, setContract] = useState<ContractReviewDetail | null>(null);
  const [logs, setLogs] = useState<ReviewLogItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [zoom, setZoom] = useState(100);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [comment, setComment] = useState("");
  const [isAiReviewing, setIsAiReviewing] = useState(false);
  const [aiReviewProgress, setAiReviewProgress] = useState<{
    step: string;
    progress: number;
    foundCount: number;
  } | null>(null);
  const [aiReport, setAiReport] = useState<{
    risk_summary: { high: number; medium: number; low: number };
    risk_items: Array<{
      id: string;
      level: string;
      title: string;
      reason: string;
      original_text?: string;
      suggested_text?: string;
      applied?: boolean;
    }>;
  } | null>(null);
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState<{
    id: string;
    title: string;
    original_text: string;
    suggested_text: string;
  } | null>(null);
  const [isFormatting, setIsFormatting] = useState(false);
  const [showFormatModal, setShowFormatModal] = useState(false);
  const [formattedContent, setFormattedContent] = useState<string>("");

  // 加载合同详情
  const loadContract = async () => {
    if (!id) return;
    setIsLoading(true);
    try {
      const [detail, logRes] = await Promise.all([
        contractReviewApi.getContractDetail(parseInt(id)),
        contractReviewApi.getReviewLogs(parseInt(id))
      ]);
      setContract(detail);
      setLogs(logRes.items);

      // 尝试加载AI审核报告（如果有）
      try {
        const reportRes = await contractReviewApi.getReviewReport(parseInt(id));
        if (reportRes.report) {
          setAiReport({
            risk_summary: reportRes.report.risk_summary,
            risk_items: reportRes.report.risk_items
          });
        }
      } catch (e) {
        // 没有报告是正常的，不报错
        console.log('暂无AI审核报告');
      }
    } catch (error) {
      toast.error('加载合同详情失败');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadContract();
  }, [id]);

  // 提交审核
  const handleSubmitReview = async () => {
    if (!contract) return;
    try {
      await contractReviewApi.submitReview(contract.id);
      toast.success('已提交审核');
      loadContract();
    } catch (error) {
      toast.error('提交失败');
    }
  };

  // 开始审核
  const handleStartReview = async () => {
    if (!contract) return;
    try {
      await contractReviewApi.startReview(contract.id);
      toast.success('已开始审核');
      loadContract();
    } catch (error) {
      toast.error('操作失败');
    }
  };

  // AI审核（带进度显示）
  const handleAiReview = async () => {
    if (!contract) return;
    setIsAiReviewing(true);
    setAiReviewProgress({ step: '准备中...', progress: 0, foundCount: 0 });

    try {
      const token = localStorage.getItem('staff_token') || '';
      const result = await contractReviewApi.aiReviewStream(
        contract.id,
        (data) => {
          // 更新进度
          if (data.step) {
            setAiReviewProgress({
              step: data.step,
              progress: data.progress,
              foundCount: data.found_count || 0
            });
          }
        },
        token
      );

      toast.success('AI审核完成');
      setAiReport(result.report);
      setContract(prev => prev ? { ...prev, status: result.new_status } : null);
    } catch (error: any) {
      toast.error(error?.message || 'AI审核失败');
    } finally {
      setIsAiReviewing(false);
      setAiReviewProgress(null);
    }
  };

  // 初审通过
  const handleFirstReviewPass = async () => {
    if (!contract) return;
    try {
      await contractReviewApi.firstReviewPass(contract.id, comment);
      toast.success('初审通过，已提交终审');
      loadContract();
    } catch (error) {
      toast.error('操作失败');
    }
  };

  // 终审通过
  const handleFinalPass = async () => {
    if (!contract) return;
    try {
      await contractReviewApi.finalReview(contract.id, 'pass', { comment });
      toast.success('终审通过，合同已完成');
      loadContract();
    } catch (error) {
      toast.error('操作失败');
    }
  };

  // 终审驳回
  const handleFinalReject = async () => {
    if (!contract || !rejectReason.trim()) {
      toast.error('请填写驳回原因');
      return;
    }
    try {
      await contractReviewApi.finalReview(contract.id, 'reject', { reject_reason: rejectReason });
      toast.success('已驳回合同');
      setShowRejectModal(false);
      setRejectReason("");
      loadContract();
    } catch (error) {
      toast.error('操作失败');
    }
  };

  // admin直接完成
  const handleDirectComplete = async () => {
    if (!contract) return;
    try {
      await contractReviewApi.directComplete(contract.id, comment);
      toast.success('审核完成');
      loadContract();
    } catch (error) {
      toast.error('操作失败');
    }
  };

  // 重新提交审核（驳回后）
  const handleResubmit = async () => {
    if (!contract) return;
    try {
      await contractReviewApi.resubmitReview(contract.id);
      toast.success('已重新提交审核');
      loadContract();
    } catch (error) {
      toast.error('操作失败');
    }
  };

  // 编辑合同内容
  const handleEditContent = async () => {
    if (!contract || !editContent.trim()) {
      toast.error('内容不能为空');
      return;
    }
    try {
      await contractReviewApi.editContent(contract.id, editContent);
      toast.success('合同内容已修改');
      setIsEditing(false);
      loadContract();
    } catch (error) {
      toast.error('修改失败');
    }
  };

  // 开始编辑
  const startEditing = () => {
    if (contract) {
      setEditContent(contract.content_edited || contract.content || "");
      setIsEditing(true);
    }
  };

  // 取消编辑
  const cancelEditing = () => {
    setIsEditing(false);
    setEditContent("");
  };

  // 打开应用建议弹窗
  const openApplyModal = (item: { id: string; title: string; original_text?: string; suggested_text?: string }) => {
    if (!item.suggested_text) {
      toast.error('该建议无可应用的内容');
      return;
    }
    setSelectedItem({
      id: item.id,
      title: item.title,
      original_text: item.original_text || '',
      suggested_text: item.suggested_text
    });
    setShowApplyModal(true);
  };

  // 应用建议到合同内容
  const handleApplySuggestion = async () => {
    if (!contract || !selectedItem) return;

    const currentContent = contract.content_edited || contract.content || '';
    let newContent = currentContent;

    if (selectedItem.original_text) {
      // 有原文，尝试智能匹配替换
      const matchResult = findAndReplace(currentContent, selectedItem.original_text, selectedItem.suggested_text);

      if (matchResult.found) {
        newContent = matchResult.content;
      } else {
        toast.error('未在合同中找到匹配的原文内容');
        return;
      }
    } else {
      // 没有原文（缺失条款），追加到末尾
      newContent = currentContent + '\n\n' + selectedItem.suggested_text;
    }

    try {
      // 1. 更新合同内容
      await contractReviewApi.editContent(contract.id, newContent);

      // 2. 标记建议为已采纳（持久化到数据库）
      await contractReviewApi.applySuggestion(contract.id, selectedItem.id);

      toast.success('建议已应用到合同');

      setShowApplyModal(false);
      setSelectedItem(null);

      // 3. 重新加载数据
      loadContract();
    } catch (error) {
      toast.error('应用失败');
    }
  };

  // 智能查找并替换原文
  const findAndReplace = (content: string, original: string, suggested: string): { found: boolean; content: string } => {
    // 1. 首先尝试精确匹配
    if (content.includes(original)) {
      return { found: true, content: content.replace(original, suggested) };
    }

    // 2. 提取原文的核心关键词（去掉标点，取前15个字符作为关键词）
    const cleanOriginal = original.replace(/[，。！？、；：""''（）【】《》\s]/g, '');
    const keywords = cleanOriginal.substring(0, 20);

    if (keywords.length < 5) {
      return { found: false, content };
    }

    // 3. 在内容中搜索包含关键词的句子
    const sentences = content.split(/([，。！？；\n]+)/);
    for (let i = 0; i < sentences.length; i++) {
      const sentence = sentences[i];
      const cleanSentence = sentence.replace(/[，。！？、；：""''（）【】《》\s]/g, '');

      // 如果句子包含关键词的一部分
      if (cleanSentence.includes(keywords.substring(0, 10)) || keywords.includes(cleanSentence.substring(0, 10))) {
        // 找到了匹配的句子，进行替换
        sentences[i] = suggested;
        // 如果下一句是标点，也去掉（因为建议文本自带标点）
        if (i + 1 < sentences.length && /^[，。！？、；：\s]+$/.test(sentences[i + 1])) {
          sentences.splice(i + 1, 1);
        }
        return { found: true, content: sentences.join('') };
      }
    }

    // 4. 更宽松的匹配：查找包含主要数字或关键信息的句子
    const numbers = original.match(/[\d,，.．]+/g);
    if (numbers && numbers.length > 0) {
      const numPattern = numbers[0].replace(/[,，.．]/g, '[,，.．]?');
      const regex = new RegExp(`[^，。！？；\n]*${numPattern}[^，。！？；\n]*`, 'g');
      const matches = content.match(regex);
      if (matches && matches.length > 0) {
        // 找到包含相同数字的句子
        const matched = matches.find(m => {
          const cleanM = m.replace(/[，。！？、；：""''（）【】《》\s]/g, '');
          return cleanM.includes(keywords.substring(0, 5)) || keywords.includes(cleanM.substring(0, 5));
        });
        if (matched) {
          return { found: true, content: content.replace(matched, suggested) };
        }
      }
    }

    return { found: false, content };
  };

  // 格式化合同内容
  const handleFormatContract = async () => {
    if (!contract) return;
    setIsFormatting(true);
    try {
      const result = await contractReviewApi.formatContract(contract.id);
      setFormattedContent(result.formatted_content);
      setShowFormatModal(true);
    } catch (error: any) {
      toast.error(error?.message || '格式化失败');
    } finally {
      setIsFormatting(false);
    }
  };

  // 应用格式化结果
  const handleApplyFormat = async () => {
    if (!contract || !formattedContent) return;
    try {
      await contractReviewApi.applyFormat(contract.id, formattedContent);
      toast.success('格式已应用到合同');
      setShowFormatModal(false);
      setFormattedContent("");
      loadContract();
    } catch (error) {
      toast.error('应用失败');
    }
  };

  // 格式化时间
  const formatTime = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  // 获取操作日志描述
  const getActionLabel = (action: string): string => {
    const actionMap: Record<string, string> = {
      submit_review: '提交审核',
      assign_reviewer: '分配审核人',
      start_review: '开始审核',
      first_review_pass: '初审通过',
      final_review_pass: '终审通过',
      final_review_reject: '驳回合同',
      direct_complete: '直接完成',
      edit_content: '编辑合同内容',
      resubmit_review: '重新提交',
    };
    return actionMap[action] || action;
  };

  if (isLoading) {
    return (
      <div className="h-[calc(100vh-140px)] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  if (!contract) {
    return (
      <div className="h-[calc(100vh-140px)] flex items-center justify-center text-slate-500">
        合同不存在
      </div>
    );
  }

  const statusInfo = statusMap[contract.status] || { label: contract.status, color: 'bg-slate-100 text-slate-600' };

  return (
    <div className="h-[calc(100vh-140px)] flex flex-col gap-6 animate-in fade-in duration-700">
      {/* Header Info */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2 rounded-lg hover:bg-slate-200 text-slate-500 transition-colors border border-slate-200 bg-white shadow-sm"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-slate-900 leading-none">
                {contract.title || contract.contract_no}
              </h2>
              <span className={cn("px-2 py-0.5 text-[10px] font-bold rounded uppercase", statusInfo.color)}>
                {statusInfo.label}
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium">
              编号: {contract.contract_no} • 用户: {contract.user_name || '-'} • {formatTime(contract.created_at)}
            </p>
          </div>
        </div>

        {/* 操作按钮区 */}
        <div className="flex items-center gap-3">
          {/* 草稿状态 */}
          {contract.status === 'draft' && (
            <button
              onClick={handleSubmitReview}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 transition-colors shadow-sm"
            >
              <Send className="w-4 h-4" />
              提交审核
            </button>
          )}

          {/* 待审核状态 */}
          {contract.status === 'pending_review' && (
            <>
              <button
                onClick={handleAiReview}
                disabled={isAiReviewing}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-semibold hover:bg-purple-700 transition-colors shadow-sm disabled:opacity-50"
              >
                {isAiReviewing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                {isAiReviewing ? 'AI正在审核' : 'AI审核'}
              </button>
              <button
                onClick={handleStartReview}
                disabled={isAiReviewing}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Check className="w-4 h-4" />
                开始审核
              </button>
              <button
                onClick={handleDirectComplete}
                disabled={isAiReviewing}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <CheckCircle className="w-4 h-4" />
                直接完成
              </button>
            </>
          )}

          {/* AI已初审状态 */}
          {contract.status === 'ai_reviewed' && (
            <>
              <button
                disabled
                className="flex items-center gap-2 px-4 py-2 bg-slate-400 text-white rounded-lg text-sm font-semibold cursor-not-allowed"
              >
                <CheckCircle className="w-4 h-4" />
                AI已审核
              </button>
              <button
                onClick={handleStartReview}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 transition-colors shadow-sm"
              >
                <Check className="w-4 h-4" />
                开始审核
              </button>
              <button
                onClick={handleDirectComplete}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700 transition-colors shadow-sm"
              >
                <CheckCircle className="w-4 h-4" />
                直接完成
              </button>
            </>
          )}

          {/* 审核中状态 */}
          {contract.status === 'in_review' && (
            <>
              <button
                onClick={handleAiReview}
                disabled={isAiReviewing}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-semibold hover:bg-purple-700 transition-colors shadow-sm disabled:opacity-50"
              >
                {isAiReviewing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                {isAiReviewing ? 'AI正在审核' : 'AI审核'}
              </button>
              <button
                onClick={startEditing}
                disabled={isAiReviewing}
                className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Edit3 className="w-4 h-4" />
                编辑合同
              </button>
              <button
                onClick={handleFirstReviewPass}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 transition-colors shadow-sm"
              >
                <Send className="w-4 h-4" />
                初审通过
              </button>
              <button
                onClick={handleDirectComplete}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700 transition-colors shadow-sm"
              >
                <CheckCircle className="w-4 h-4" />
                直接完成
              </button>
            </>
          )}

          {/* 等待终审状态 */}
          {contract.status === 'pending_manager' && (
            <>
              <button
                onClick={startEditing}
                className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-sm"
              >
                <Edit3 className="w-4 h-4" />
                编辑合同
              </button>
              <button
                onClick={handleFinalPass}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700 transition-colors shadow-sm"
              >
                <CheckCircle className="w-4 h-4" />
                终审通过
              </button>
              <button
                onClick={() => setShowRejectModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-rose-600 text-white rounded-lg text-sm font-semibold hover:bg-rose-700 transition-colors shadow-sm"
              >
                <X className="w-4 h-4" />
                驳回
              </button>
            </>
          )}

          {/* 已驳回状态 */}
          {contract.status === 'rejected' && (
            <>
              <button
                onClick={handleResubmit}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 transition-colors shadow-sm"
              >
                <RotateCcw className="w-4 h-4" />
                重新提交
              </button>
              <button
                onClick={handleDirectComplete}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700 transition-colors shadow-sm"
              >
                <CheckCircle className="w-4 h-4" />
                直接完成
              </button>
            </>
          )}
        </div>

        {/* AI审核进度条 */}
        {isAiReviewing && aiReviewProgress && (
          <div className="mt-3 p-4 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-xl border border-purple-100">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-purple-700">{aiReviewProgress.step}</span>
              <span className="text-sm font-bold text-purple-600">{aiReviewProgress.progress}%</span>
            </div>
            <div className="w-full bg-purple-100 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-gradient-to-r from-purple-500 to-indigo-500 h-2.5 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${aiReviewProgress.progress}%` }}
              />
            </div>
            {aiReviewProgress.foundCount > 0 && (
              <p className="text-xs text-purple-600 mt-2">已发现 {aiReviewProgress.foundCount} 个问题</p>
            )}
          </div>
        )}
      </div>

      {/* Main Review Workspace */}
      <div className="flex-1 flex gap-6 overflow-hidden min-h-0">
        {/* Left: Document Preview */}
        <div className="flex-1 bg-slate-200 rounded-2xl overflow-hidden flex flex-col border border-slate-300 relative shadow-inner">
          <div className="h-12 bg-slate-100 border-b border-slate-200 flex items-center justify-between px-4 shrink-0">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1 bg-white border border-slate-200 rounded-md p-0.5 shadow-sm">
                <button onClick={() => setZoom(z => Math.max(50, z - 10))} className="p-1 hover:bg-slate-50 rounded text-slate-500"><Minus className="w-3 h-3" /></button>
                <span className="text-[10px] font-bold text-slate-600 w-10 text-center">{zoom}%</span>
                <button onClick={() => setZoom(z => Math.min(200, z + 10))} className="p-1 hover:bg-slate-50 rounded text-slate-500"><Plus className="w-3 h-3" /></button>
              </div>
              <button className="p-1.5 hover:bg-white rounded text-slate-500 transition-colors"><RotateCcw className="w-3 h-3" /></button>
            </div>
            <div className="flex items-center gap-2">
              {/* 编辑模式按钮 */}
              {isEditing ? (
                <>
                  <button
                    onClick={handleEditContent}
                    className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-700"
                  >
                    <Check className="w-3.5 h-3.5" />
                    保存
                  </button>
                  <button
                    onClick={cancelEditing}
                    className="flex items-center gap-1 px-3 py-1.5 bg-slate-200 text-slate-600 rounded-lg text-xs font-semibold hover:bg-slate-300"
                  >
                    <X className="w-3.5 h-3.5" />
                    取消
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={startEditing}
                    className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    编辑
                  </button>
                  <button
                    onClick={handleFormatContract}
                    disabled={isFormatting}
                    className="flex items-center gap-1 px-3 py-1.5 bg-purple-600 text-white rounded-lg text-xs font-semibold hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isFormatting ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <AlignLeft className="w-3.5 h-3.5" />
                    )}
                    {isFormatting ? '整理中...' : '整理格式'}
                  </button>
                </>
              )}
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
                <input type="text" placeholder="在文档中搜索..." className="bg-white border border-slate-200 rounded-lg pl-8 pr-3 py-1 text-[11px] focus:ring-1 focus:ring-indigo-500" />
              </div>
              <button className="p-1.5 hover:bg-white rounded text-slate-500 transition-colors"><Maximize2 className="w-3 h-3" /></button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto bg-slate-500/10 p-12 flex justify-center scrollbar-thin scrollbar-thumb-slate-400 scrollbar-track-transparent">
            <div
              className="bg-white shadow-2xl rounded-sm w-full max-w-[800px] min-h-[1100px] p-20 relative transition-transform origin-top"
              style={{ transform: `scale(${zoom / 100})` }}
            >
              {isEditing ? (
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="w-full h-full min-h-[1000px] font-serif text-slate-800 text-base leading-relaxed resize-none focus:outline-none"
                  placeholder="输入合同内容..."
                />
              ) : (
                <div className="space-y-8 font-serif leading-relaxed text-slate-800 whitespace-pre-wrap">
                  {contract.content_edited || contract.content || "暂无合同内容"}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: Review Info Panel */}
        <div className="w-[450px] shrink-0 flex flex-col gap-6">
          {/* 审核信息 */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4 flex flex-col shrink-0">
            <h3 className="font-bold text-slate-900">审核信息</h3>

            {/* 初审信息 */}
            {contract.first_reviewed_by && (
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-2">初审</p>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-indigo-100 flex items-center justify-center text-[10px] font-bold text-indigo-600">
                    {contract.first_reviewed_by_name?.[0] || '?'}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{contract.first_reviewed_by_name}</p>
                    <p className="text-[10px] text-slate-500">{formatTime(contract.first_reviewed_at)}</p>
                  </div>
                </div>
                {contract.first_review_comment && (
                  <p className="text-xs text-slate-600 mt-2 bg-white p-2 rounded-lg">{contract.first_review_comment}</p>
                )}
              </div>
            )}

            {/* 终审信息 */}
            {contract.final_reviewed_by && (
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-2">终审</p>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-emerald-100 flex items-center justify-center text-[10px] font-bold text-emerald-600">
                    {contract.final_reviewed_by_name?.[0] || '?'}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{contract.final_reviewed_by_name}</p>
                    <p className="text-[10px] text-slate-500">{formatTime(contract.final_reviewed_at)}</p>
                  </div>
                </div>
                {contract.final_review_comment && (
                  <p className="text-xs text-slate-600 mt-2 bg-white p-2 rounded-lg">{contract.final_review_comment}</p>
                )}
              </div>
            )}

            {/* 驳回信息 */}
            {contract.rejected_by && (
              <div className="bg-rose-50 p-3 rounded-xl border border-rose-100">
                <p className="text-[10px] text-rose-500 font-bold uppercase tracking-wider mb-2">已驳回</p>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-rose-100 flex items-center justify-center text-[10px] font-bold text-rose-600">
                    {contract.rejected_by_name?.[0] || '?'}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{contract.rejected_by_name}</p>
                    <p className="text-[10px] text-slate-500">{formatTime(contract.rejected_at)}</p>
                  </div>
                </div>
                {contract.reject_reason && (
                  <p className="text-xs text-rose-600 mt-2 bg-white p-2 rounded-lg">{contract.reject_reason}</p>
                )}
              </div>
            )}

            {/* 合同编辑信息 */}
            {contract.content_edited_by && (
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-2">内容修改</p>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-amber-100 flex items-center justify-center text-[10px] font-bold text-amber-600">
                    {contract.content_edited_by_name?.[0] || '?'}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{contract.content_edited_by_name}</p>
                    <p className="text-[10px] text-slate-500">{formatTime(contract.content_edited_at)}</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* AI审核报告 */}
          {(aiReport || contract.status === 'ai_reviewed') && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4 flex flex-col shrink-0">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-slate-900 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-600" />
                  AI审核报告
                </h3>
                {aiReport && (
                  <div className="flex gap-2">
                    {aiReport.risk_summary.high > 0 && (
                      <span className="px-2 py-0.5 bg-rose-50 text-rose-600 text-[10px] font-bold rounded">
                        高风险 {aiReport.risk_summary.high}
                      </span>
                    )}
                    {aiReport.risk_summary.medium > 0 && (
                      <span className="px-2 py-0.5 bg-amber-50 text-amber-600 text-[10px] font-bold rounded">
                        中风险 {aiReport.risk_summary.medium}
                      </span>
                    )}
                    {aiReport.risk_summary.low > 0 && (
                      <span className="px-2 py-0.5 bg-yellow-50 text-yellow-600 text-[10px] font-bold rounded">
                        低风险 {aiReport.risk_summary.low}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {aiReport && aiReport.risk_items.length > 0 && (
                <div className="space-y-3 max-h-[300px] overflow-y-auto">
                  {aiReport.risk_items.map((item) => (
                    <div
                      key={item.id}
                      className={cn(
                        "p-3 rounded-xl border",
                        item.level === 'high'
                          ? "border-rose-200 bg-rose-50/50"
                          : item.level === 'medium'
                          ? "border-amber-200 bg-amber-50/50"
                          : "border-yellow-200 bg-yellow-50/50"
                      )}
                    >
                      <div className="flex items-start gap-2">
                        <div className={cn(
                          "w-6 h-6 rounded-full flex items-center justify-center shrink-0",
                          item.level === 'high'
                            ? "bg-rose-100 text-rose-600"
                            : item.level === 'medium'
                            ? "bg-amber-100 text-amber-600"
                            : "bg-yellow-100 text-yellow-600"
                        )}>
                          <AlertCircle className="w-3 h-3" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-semibold text-slate-900">{item.title}</p>
                              {item.applied && (
                                <span className="px-2 py-0.5 text-[10px] font-bold bg-emerald-50 text-emerald-600 rounded flex items-center gap-1">
                                  <CheckCircle className="w-3 h-3" />
                                  已采纳
                                </span>
                              )}
                            </div>
                            {item.suggested_text && !item.applied && (
                              <button
                                onClick={() => openApplyModal(item)}
                                className="px-2 py-1 text-[10px] font-bold bg-indigo-50 text-indigo-600 rounded hover:bg-indigo-100 transition-colors shrink-0"
                              >
                                应用建议
                              </button>
                            )}
                          </div>
                          <p className="text-xs text-slate-500 mt-1">{item.reason}</p>
                          {item.original_text && (
                            <div className="mt-2 p-2 bg-slate-50 rounded-lg border border-slate-200">
                              <p className="text-[10px] text-slate-400 font-medium mb-1">原文：</p>
                              <p className={cn("text-xs text-slate-600", item.applied && "line-through")}>{item.original_text}</p>
                            </div>
                          )}
                          {item.suggested_text && (
                            <div className={cn("mt-2 p-2 rounded-lg border", item.applied ? "bg-emerald-100 border-emerald-300" : "bg-emerald-50 border-emerald-200")}>
                              <p className="text-[10px] text-emerald-500 font-medium mb-1">{item.applied ? "已修改为：" : "建议修改为："}</p>
                              <p className="text-xs text-emerald-700">{item.suggested_text}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 审核日志 */}
          <div className="flex-1 bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col overflow-hidden min-h-0">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <span className="text-sm font-bold text-slate-900">审核记录</span>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin scrollbar-thumb-slate-200">
              {logs.length === 0 ? (
                <div className="text-center text-slate-400 text-sm py-8">暂无审核记录</div>
              ) : (
                logs.map((log) => (
                  <div key={log.id} className="flex items-start gap-3 p-3 bg-slate-50 rounded-xl">
                    <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-[10px] font-bold text-slate-600 shrink-0">
                      {log.operator_name?.[0] || '?'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold text-slate-900">{log.operator_name}</span>
                        <span className="text-[10px] text-slate-400">{formatTime(log.created_at)}</span>
                      </div>
                      <p className="text-xs text-slate-600">{getActionLabel(log.action)}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 驳回弹窗 */}
      <AnimatePresence>
        {showRejectModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setShowRejectModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-2xl shadow-2xl w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6 border-b border-slate-200">
                <h3 className="text-lg font-bold text-slate-900">驳回合同</h3>
              </div>
              <div className="p-6">
                <label className="block text-sm font-semibold text-slate-700 mb-2">驳回原因 *</label>
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  className="w-full h-32 p-3 border border-slate-200 rounded-xl text-sm resize-none focus:ring-1 focus:ring-rose-500"
                  placeholder="请输入驳回原因..."
                />
              </div>
              <div className="p-6 border-t border-slate-200 flex justify-end gap-3">
                <button
                  onClick={() => setShowRejectModal(false)}
                  className="px-4 py-2 bg-slate-100 text-slate-600 rounded-lg text-sm font-semibold hover:bg-slate-200"
                >
                  取消
                </button>
                <button
                  onClick={handleFinalReject}
                  className="px-4 py-2 bg-rose-600 text-white rounded-lg text-sm font-semibold hover:bg-rose-700"
                >
                  确认驳回
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 应用建议弹窗 */}
      <AnimatePresence>
        {showApplyModal && selectedItem && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setShowApplyModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6 border-b border-slate-200">
                <h3 className="text-lg font-bold text-slate-900">应用建议：{selectedItem.title}</h3>
              </div>
              <div className="p-6 space-y-4 max-h-[50vh] overflow-y-auto">
                {selectedItem.original_text ? (
                  <>
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-2">原文内容（将被替换）</label>
                      <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-600">
                        {selectedItem.original_text}
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-2">修改后内容</label>
                      <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-sm text-emerald-700">
                        {selectedItem.suggested_text}
                      </div>
                    </div>
                  </>
                ) : (
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-2">将添加以下内容到合同末尾</label>
                    <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-sm text-emerald-700 whitespace-pre-wrap">
                      {selectedItem.suggested_text}
                    </div>
                  </div>
                )}
              </div>
              <div className="p-6 border-t border-slate-200 flex justify-end gap-3">
                <button
                  onClick={() => {
                    setShowApplyModal(false);
                    setSelectedItem(null);
                  }}
                  className="px-4 py-2 bg-slate-100 text-slate-600 rounded-lg text-sm font-semibold hover:bg-slate-200"
                >
                  取消
                </button>
                <button
                  onClick={handleApplySuggestion}
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700"
                >
                  确认应用
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 格式化预览弹窗 */}
      <AnimatePresence>
        {showFormatModal && formattedContent && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setShowFormatModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[85vh] overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6 border-b border-slate-200 flex items-center justify-between">
                <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <AlignLeft className="w-5 h-5 text-purple-600" />
                  格式化预览
                </h3>
                <p className="text-sm text-slate-500">AI已整理合同格式，请预览后确认应用</p>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">格式化后的合同内容</label>
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-700 max-h-[50vh] overflow-y-auto whitespace-pre-wrap font-serif leading-relaxed">
                    {formattedContent}
                  </div>
                </div>
              </div>
              <div className="p-6 border-t border-slate-200 flex justify-end gap-3">
                <button
                  onClick={() => {
                    setShowFormatModal(false);
                    setFormattedContent("");
                  }}
                  className="px-4 py-2 bg-slate-100 text-slate-600 rounded-lg text-sm font-semibold hover:bg-slate-200"
                >
                  取消
                </button>
                <button
                  onClick={handleApplyFormat}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-semibold hover:bg-purple-700"
                >
                  确认应用
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
