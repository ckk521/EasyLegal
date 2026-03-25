/**
 * 可编辑合同模板组件 - 在合同原文中填写信息
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  FileText, Save, Send, AlertCircle, CheckCircle,
  Loader2, Download, Printer
} from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { toast } from 'sonner';

const API_BASE_URL = 'http://localhost:8000';

function cn(...inputs: any[]) {
  return twMerge(clsx(inputs));
}

interface ContractTemplateEditorProps {
  contractType: string;
  contractTypeName: string;
  templateContent: string;
  fields: Array<{
    name: string;
    label: string;
    type?: string;
    required?: boolean;
    placeholder?: string;
  }>;
  draftId?: number;
  draftValues?: Record<string, string>;
  sessionId?: number;  // 当前会话ID
  onSaveDraft: (values: Record<string, string>) => void;
  onSubmit: (values: Record<string, string>) => void;
  onCancel: () => void;
}

export function ContractTemplateEditor({
  contractType,
  contractTypeName,
  templateContent,
  fields,
  draftId: externalDraftId,
  draftValues = {},
  sessionId,
  onSaveDraft,
  onSubmit,
  onCancel
}: ContractTemplateEditorProps) {
  const [values, setValues] = useState<Record<string, string>>(draftValues);
  const [errors, setErrors] = useState<Set<string>>(new Set());
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const printRef = useRef<HTMLDivElement>(null);

  // 内部维护的草稿ID，防止重复创建
  const [internalDraftId, setInternalDraftId] = useState<number | null>(externalDraftId || null);
  // 防止自动保存重复调用的标志
  const isSavingRef = useRef(false);

  // 同步外部 draftId 到内部状态
  useEffect(() => {
    if (externalDraftId && externalDraftId !== internalDraftId) {
      setInternalDraftId(externalDraftId);
    }
  }, [externalDraftId]);

  // 当 draftValues 从外部更新时（如草稿恢复），同步到 values 状态
  useEffect(() => {
    if (Object.keys(draftValues).length > 0) {
      setValues(draftValues);
    }
  }, [draftValues]);

  // 自动保存 - 使用 internalDraftId 防止重复创建
  useEffect(() => {
    const timer = setTimeout(() => {
      if (Object.keys(values).length > 0 && !isSavingRef.current) {
        performSaveDraft(values, true);
      }
    }, 3000);
    return () => clearTimeout(timer);
  }, [values, internalDraftId]);

  const handleChange = (fieldName: string, value: string) => {
    setValues(prev => ({ ...prev, [fieldName]: value }));
    // 清除错误状态
    if (errors.has(fieldName)) {
      setErrors(prev => {
        const next = new Set(prev);
        next.delete(fieldName);
        return next;
      });
    }
  };

  // 实际执行保存的函数
  const performSaveDraft = async (valuesToSave: Record<string, string>, silent = false) => {
    if (isSavingRef.current) return; // 防止重复调用
    isSavingRef.current = true;

    if (!silent) setIsSaving(true);

    try {
      const token = localStorage.getItem('user_token');
      const currentDraftId = internalDraftId;

      if (currentDraftId) {
        // 更新现有草稿
        await fetch(`${API_BASE_URL}/api/contract-drafts/${currentDraftId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ field_values: valuesToSave })
        });
      } else {
        // 创建新草稿
        const response = await fetch(`${API_BASE_URL}/api/contract-drafts`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            contract_type: contractType,
            field_values: valuesToSave,
            session_id: sessionId  // 传入会话ID
          })
        });
        if (response.ok) {
          const data = await response.json();
          setInternalDraftId(data.id); // 保存新创建的 draftId
          onSaveDraft(valuesToSave);
        }
      }

      if (!silent) {
        toast.success('草稿已保存');
      }
    } catch (error) {
      if (!silent) {
        toast.error('保存失败');
      }
    } finally {
      isSavingRef.current = false;
      if (!silent) setIsSaving(false);
    }
  };

  // 手动保存按钮调用
  const handleSaveDraft = () => {
    performSaveDraft(values, false);
  };

  const validateFields = (): boolean => {
    const requiredFields = fields.filter(f => f.required).map(f => f.name);
    const missingFields = new Set<string>();

    requiredFields.forEach(name => {
      if (!values[name]?.trim()) {
        missingFields.add(name);
      }
    });

    setErrors(missingFields);
    return missingFields.size === 0;
  };

  const handleSubmit = async () => {
    if (!validateFields()) {
      toast.error('请填写所有必填项');
      return;
    }

    setIsSubmitting(true);

    try {
      const token = localStorage.getItem('user_token');
      let currentDraftId = internalDraftId;

      if (!currentDraftId) {
        const createRes = await fetch(`${API_BASE_URL}/api/contract-drafts`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            contract_type: contractType,
            field_values: values,
            session_id: sessionId  // 传入会话ID
          })
        });

        if (createRes.ok) {
          const data = await createRes.json();
          currentDraftId = data.id;
          setInternalDraftId(data.id);
        }
      } else {
        await fetch(`${API_BASE_URL}/api/contract-drafts/${currentDraftId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ field_values: values })
        });
      }

      const completeRes = await fetch(`${API_BASE_URL}/api/contract-drafts/${currentDraftId}/complete`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (completeRes.ok) {
        toast.success('合同生成成功！');
        onSubmit(values);
      } else {
        const error = await completeRes.json();
        toast.error(error.detail || '生成失败');
      }
    } catch (error) {
      toast.error('提交失败，请重试');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 解析模板并渲染
  const renderTemplate = () => {
    // 匹配 【变量名】 格式
    const parts = templateContent.split(/(【[^】]+】)/g);

    return parts.map((part, index) => {
      const match = part.match(/【([^】]+)】/);
      if (match) {
        const fieldName = match[1];
        const field = fields.find(f => f.name === fieldName || f.label === fieldName);

        if (field) {
          const hasError = errors.has(field.name);
          return (
            <InlineInput
              key={index}
              fieldName={field.name}
              value={values[field.name] || ''}
              placeholder={field.placeholder || `请输入${field.label}`}
              required={field.required}
              hasError={hasError}
              onChange={(v) => handleChange(field.name, v)}
            />
          );
        } else {
          // 没有字段定义，使用变量名
          const hasError = errors.has(fieldName);
          return (
            <InlineInput
              key={index}
              fieldName={fieldName}
              value={values[fieldName] || ''}
              placeholder={`请输入${fieldName}`}
              required={false}
              hasError={hasError}
              onChange={(v) => handleChange(fieldName, v)}
            />
          );
        }
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className="w-full max-w-3xl">
      {/* 头部 */}
      <div className="bg-gradient-to-r from-slate-800 to-slate-700 rounded-t-2xl p-6 text-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-bold">{contractTypeName}</h3>
              <p className="text-sm text-white/70">请在合同中填写相关信息</p>
            </div>
          </div>
          {internalDraftId && (
            <div className="flex items-center gap-2 text-sm text-white/60">
              <Save className="w-3 h-3" />
              <span>自动保存中</span>
            </div>
          )}
        </div>
      </div>

      {/* 合同内容 */}
      <div
        ref={printRef}
        className="bg-white border border-slate-200 border-t-0 p-8 space-y-4"
        style={{ minHeight: '400px' }}
      >
        {/* 提示 */}
        <div className="flex items-center gap-2 p-3 bg-blue-50 rounded-lg text-sm text-blue-700 mb-6">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>高亮区域为需要填写的信息，填写完成后点击"生成合同"</span>
        </div>

        {/* 合同正文 */}
        <div className="prose prose-slate max-w-none text-slate-800 leading-relaxed whitespace-pre-wrap">
          {renderTemplate()}
        </div>
      </div>

      {/* 底部操作栏 */}
      <div className="bg-slate-50 border border-slate-200 border-t-0 rounded-b-2xl p-4">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2.5 text-sm text-slate-600 hover:text-slate-900 transition-colors"
          >
            取消
          </button>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => handleSaveDraft()}
              disabled={isSaving}
              className="flex items-center gap-2 px-4 py-2.5 text-sm text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors disabled:opacity-50"
            >
              {isSaving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              保存草稿
            </button>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="flex items-center gap-2 px-6 py-2.5 text-sm font-bold text-white bg-blue-600 rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50 shadow-lg shadow-blue-600/25"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <CheckCircle className="w-4 h-4" />
              )}
              生成合同
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==================== 行内输入组件 ====================

interface InlineInputProps {
  fieldName: string;
  value: string;
  placeholder: string;
  required?: boolean;
  hasError?: boolean;
  onChange: (value: string) => void;
}

function InlineInput({
  fieldName,
  value,
  placeholder,
  required,
  hasError,
  onChange
}: InlineInputProps) {
  const [isFocused, setIsFocused] = useState(false);

  return (
    <span
      className={cn(
        "inline-flex items-center mx-0.5 rounded transition-all",
        isFocused ? "bg-blue-50" : "bg-amber-50",
        hasError && "bg-red-50 ring-1 ring-red-300"
      )}
    >
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setIsFocused(false)}
        placeholder={placeholder}
        className={cn(
          "bg-transparent border-none outline-none text-center px-2 py-1 min-w-[100px] text-slate-800",
          "placeholder:text-slate-400 placeholder:text-sm",
          isFocused && "text-blue-700",
          hasError && "text-red-600"
        )}
        style={{ width: value ? `${Math.max(100, value.length * 14 + 20)}px` : undefined }}
      />
      {required && !value && (
        <span className="text-red-400 text-xs mr-1">*</span>
      )}
    </span>
  );
}
