/**
 * 草稿夹页面 - 管理未完成的合同草稿
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { toast } from 'sonner';
import {
  FileText, Clock, Trash2, Edit3, CheckCircle, AlertCircle,
  Loader2, FileCheck, ChevronRight
} from 'lucide-react';
import { contractDraftApi, ContractDraftItem } from '../../services/api';

export function DraftsFolder() {
  const [drafts, setDrafts] = useState<ContractDraftItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadDrafts();
  }, []);

  const loadDrafts = async () => {
    setIsLoading(true);
    try {
      const data = await contractDraftApi.listDrafts();
      setDrafts(data);
    } catch (error) {
      console.error('加载草稿失败:', error);
      toast.error('加载草稿失败');
    }
    setIsLoading(false);
  };

  const handleDelete = async (draftId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('确定要删除这份草稿吗？')) return;

    try {
      await contractDraftApi.deleteDraft(draftId);
      toast.success('删除成功');
      loadDrafts();
    } catch (error: any) {
      toast.error('删除失败: ' + error.message);
    }
  };

  const handleContinue = (draft: ContractDraftItem) => {
    // 跳转到对话页面，并传递草稿ID
    navigate(`/?draft=${draft.id}`);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      const hours = Math.floor(diff / (1000 * 60 * 60));
      if (hours === 0) {
        const minutes = Math.floor(diff / (1000 * 60));
        return minutes <= 1 ? '刚刚' : `${minutes}分钟前`;
      }
      return `${hours}小时前`;
    } else if (days === 1) {
      return '昨天';
    } else if (days < 7) {
      return `${days}天前`;
    } else {
      return date.toLocaleDateString('zh-CN');
    }
  };

  const getCompletionProgress = (draft: ContractDraftItem) => {
    const requiredFields = draft.fields_definition.filter(f => f.required);
    if (requiredFields.length === 0) return 100;

    const filledCount = requiredFields.filter(f => draft.field_values[f.name]).length;
    return Math.round((filledCount / requiredFields.length) * 100);
  };

  // 分离草稿和已完成的合同
  const pendingDrafts = drafts.filter(d => d.status === 'draft');
  const completedContracts = drafts.filter(d => d.status === 'completed');

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* 页面标题 */}
        <div className="space-y-1">
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">草稿夹</h2>
          <p className="text-sm text-slate-500">管理您的合同草稿，随时继续填写</p>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          </div>
        ) : (
          <>
            {/* 未完成草稿 */}
            <section>
              <div className="flex items-center gap-2 mb-4">
                <Edit3 className="w-5 h-5 text-amber-500" />
                <h3 className="font-semibold text-slate-900">待填写草稿</h3>
                {pendingDrafts.length > 0 && (
                  <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs font-medium rounded-full">
                    {pendingDrafts.length}
                  </span>
                )}
              </div>

              {pendingDrafts.length === 0 ? (
                <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
                  <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                  <p className="text-slate-500">暂无未完成的草稿</p>
                  <p className="text-sm text-slate-400 mt-1">在对话中生成合同时会自动保存草稿</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {pendingDrafts.map((draft) => {
                    const progress = getCompletionProgress(draft);
                    return (
                      <div
                        key={draft.id}
                        onClick={() => handleContinue(draft)}
                        className="bg-white rounded-xl border border-slate-200 p-4 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer group"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-4">
                            <div className="w-12 h-12 rounded-lg bg-amber-50 flex items-center justify-center shrink-0">
                              <FileText className="w-6 h-6 text-amber-500" />
                            </div>
                            <div className="space-y-1">
                              <h4 className="font-medium text-slate-900 group-hover:text-blue-600 transition-colors">
                                {draft.contract_type} - {draft.contract_no}
                              </h4>
                              <div className="flex items-center gap-3 text-sm text-slate-500">
                                <span className="flex items-center gap-1">
                                  <Clock className="w-3.5 h-3.5" />
                                  {formatDate(draft.updated_at)}
                                </span>
                                <span className="text-slate-300">|</span>
                                <span>进度 {progress}%</span>
                              </div>
                              {/* 进度条 */}
                              <div className="w-48 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full transition-all ${
                                    progress === 100 ? 'bg-emerald-500' : 'bg-amber-400'
                                  }`}
                                  style={{ width: `${progress}%` }}
                                />
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="px-2.5 py-1 bg-amber-50 text-amber-600 text-xs font-medium rounded-full flex items-center gap-1">
                              <AlertCircle className="w-3 h-3" />
                              未完成
                            </span>
                            <button
                              onClick={(e) => handleDelete(draft.id, e)}
                              className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>

            {/* 已完成的合同 */}
            {completedContracts.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <CheckCircle className="w-5 h-5 text-emerald-500" />
                  <h3 className="font-semibold text-slate-900">已完成合同</h3>
                  <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs font-medium rounded-full">
                    {completedContracts.length}
                  </span>
                </div>

                <div className="space-y-3">
                  {completedContracts.map((contract) => (
                    <div
                      key={contract.id}
                      className="bg-white rounded-xl border border-slate-200 p-4 hover:shadow-md transition-all"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 rounded-lg bg-emerald-50 flex items-center justify-center">
                            <FileCheck className="w-6 h-6 text-emerald-500" />
                          </div>
                          <div>
                            <h4 className="font-medium text-slate-900">{contract.title}</h4>
                            <p className="text-sm text-slate-500">
                              {contract.contract_no} · {formatDate(contract.updated_at)}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="px-2.5 py-1 bg-emerald-50 text-emerald-600 text-xs font-medium rounded-full flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" />
                            已完成
                          </span>
                          <button
                            onClick={() => navigate(`/report/${contract.id}`)}
                            className="flex items-center gap-1 px-3 py-1.5 text-blue-600 hover:bg-blue-50 rounded-lg text-sm font-medium transition-colors"
                          >
                            查看
                            <ChevronRight className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 空状态 */}
            {drafts.length === 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
                <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-700 mb-2">草稿夹为空</h3>
                <p className="text-slate-500 mb-4">在对话中提到"签订合同"，即可开始创建合同草稿</p>
                <button
                  onClick={() => navigate('/')}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
                >
                  开始对话
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
