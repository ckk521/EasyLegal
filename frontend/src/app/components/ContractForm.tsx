/**
 * 合同生成表单组件 - 正式、专业的合同信息填写表单
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  FileText, Save, Send, RotateCcw, CheckCircle, AlertCircle,
  Building2, User, Phone, Calendar, MapPin, DollarSign, FileCheck,
  Loader2, ChevronDown, ChevronUp
} from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { toast } from 'sonner';

const API_BASE_URL = 'http://localhost:8000';

function cn(...inputs: any[]) {
  return twMerge(clsx(inputs));
}

interface FormField {
  name: string;
  label: string;
  type: 'text' | 'textarea' | 'date' | 'select';
  required?: boolean;
  placeholder?: string;
  options?: string[];
}

interface ContractFormProps {
  formData: {
    contract_type: string;
    contract_type_name: string;
    has_template: boolean;
    template_id: number | null;
    fields: FormField[];
    greeting: string;
  };
  draftId?: number;
  draftValues?: Record<string, string>;
  sessionId?: number;  // 当前会话ID
  onSaveDraft: (values: Record<string, string>) => void;
  onSubmit: (values: Record<string, string>) => void;
  onCancel: () => void;
}

export function ContractForm({
  formData,
  draftId,
  draftValues = {},
  sessionId,
  onSaveDraft,
  onSubmit,
  onCancel
}: ContractFormProps) {
  const [values, setValues] = useState<Record<string, string>>(draftValues);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showOptional, setShowOptional] = useState(false);

  // 自动保存定时器
  useEffect(() => {
    const timer = setTimeout(() => {
      if (Object.keys(values).length > 0) {
        handleSaveDraft(true); // 静默保存
      }
    }, 3000);

    return () => clearTimeout(timer);
  }, [values]);

  const handleChange = (name: string, value: string) => {
    setValues(prev => ({ ...prev, [name]: value }));
    // 清除该字段的错误
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    formData.fields.forEach(field => {
      if (field.required && !values[field.name]?.trim()) {
        newErrors[field.name] = `${field.label}为必填项`;
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSaveDraft = async (silent = false) => {
    if (!silent) setIsSaving(true);

    try {
      const token = localStorage.getItem('user_token');

      if (draftId) {
        // 更新现有草稿
        await fetch(`${API_BASE_URL}/api/contract-drafts/${draftId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ field_values: values })
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
            contract_type: formData.contract_type,
            field_values: values,
            session_id: sessionId  // 传入会话ID
          })
        });
        if (response.ok) {
          const data = await response.json();
          // 通知父组件新的draftId
          onSaveDraft(values);
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
      if (!silent) setIsSaving(false);
    }
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      toast.error('请填写所有必填项');
      return;
    }

    setIsSubmitting(true);

    try {
      const token = localStorage.getItem('user_token');

      // 先保存草稿
      let currentDraftId = draftId;

      if (!currentDraftId) {
        const createRes = await fetch(`${API_BASE_URL}/api/contract-drafts`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            contract_type: formData.contract_type,
            field_values: values,
            session_id: sessionId  // 传入会话ID
          })
        });

        if (createRes.ok) {
          const data = await createRes.json();
          currentDraftId = data.id;
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

      // 完成草稿生成合同
      const completeRes = await fetch(`${API_BASE_URL}/api/contract-drafts/${currentDraftId}/complete`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (completeRes.ok) {
        const result = await completeRes.json();
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

  // 分离必填和可选字段
  const requiredFields = formData.fields.filter(f => f.required);
  const optionalFields = formData.fields.filter(f => !f.required);

  const getFieldIcon = (fieldName: string) => {
    if (fieldName.includes('party') || fieldName.includes('甲方') || fieldName.includes('乙方')) {
      return <User className="w-4 h-4 text-slate-400" />;
    }
    if (fieldName.includes('phone') || fieldName.includes('电话') || fieldName.includes('联系')) {
      return <Phone className="w-4 h-4 text-slate-400" />;
    }
    if (fieldName.includes('date') || fieldName.includes('日期') || fieldName.includes('期限')) {
      return <Calendar className="w-4 h-4 text-slate-400" />;
    }
    if (fieldName.includes('address') || fieldName.includes('地址') || fieldName.includes('房屋')) {
      return <MapPin className="w-4 h-4 text-slate-400" />;
    }
    if (fieldName.includes('price') || fieldName.includes('租金') || fieldName.includes('金额') || fieldName.includes('押金')) {
      return <DollarSign className="w-4 h-4 text-slate-400" />;
    }
    return <FileCheck className="w-4 h-4 text-slate-400" />;
  };

  return (
    <div className="w-full max-w-2xl">
      {/* 表单头部 */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-t-2xl p-6 text-white">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold">{formData.contract_type_name}</h3>
            <p className="text-sm text-white/80">请填写以下信息生成合同</p>
          </div>
        </div>
        {draftId && (
          <div className="mt-3 flex items-center gap-2 text-sm text-white/70">
            <Save className="w-3 h-3" />
            <span>草稿已自动保存</span>
          </div>
        )}
      </div>

      {/* 表单内容 */}
      <div className="bg-white border border-slate-200 border-t-0 rounded-b-2xl p-6 space-y-6">
        {/* 提示信息 */}
        <div className="flex items-start gap-3 p-4 bg-blue-50 rounded-xl border border-blue-100">
          <AlertCircle className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-medium">填写说明</p>
            <p className="mt-1 text-blue-600">带 <span className="text-red-500">*</span> 为必填项，信息将用于生成正式合同文本。所有信息仅存储在本地，请放心填写。</p>
          </div>
        </div>

        {/* 必填字段 */}
        <div className="space-y-4">
          <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-500" />
            基本信息
            <span className="text-xs text-slate-400 font-normal">（必填）</span>
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {requiredFields.map(field => (
              <FormField
                key={field.name}
                field={field}
                value={values[field.name] || ''}
                error={errors[field.name]}
                onChange={(v) => handleChange(field.name, v)}
                icon={getFieldIcon(field.name)}
              />
            ))}
          </div>
        </div>

        {/* 可选字段 */}
        {optionalFields.length > 0 && (
          <div className="space-y-4">
            <button
              type="button"
              onClick={() => setShowOptional(!showOptional)}
              className="flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
            >
              {showOptional ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              补充信息（可选）
              <span className="text-xs text-slate-400">{optionalFields.length} 项</span>
            </button>

            {showOptional && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                {optionalFields.map(field => (
                  <FormField
                    key={field.name}
                    field={field}
                    value={values[field.name] || ''}
                    error={errors[field.name]}
                    onChange={(v) => handleChange(field.name, v)}
                    icon={getFieldIcon(field.name)}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-100">
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
              className="flex items-center gap-2 px-4 py-2.5 text-sm text-slate-600 bg-slate-100 rounded-xl hover:bg-slate-200 transition-colors disabled:opacity-50"
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
                <Send className="w-4 h-4" />
              )}
              生成合同
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==================== 表单字段组件 ====================

interface FormFieldProps {
  field: FormField;
  value: string;
  error?: string;
  onChange: (value: string) => void;
  icon?: React.ReactNode;
}

function FormField({ field, value, error, onChange, icon }: FormFieldProps) {
  const inputId = `field_${field.name}`;

  const baseInputClasses = cn(
    "w-full bg-slate-50 border rounded-xl px-4 py-3 text-sm text-slate-800",
    "placeholder:text-slate-400",
    "focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500",
    "transition-all",
    error ? "border-red-300 bg-red-50/50" : "border-slate-200 hover:border-slate-300"
  );

  return (
    <div className={cn("space-y-1.5", field.type === 'textarea' ? 'md:col-span-2' : '')}>
      <label htmlFor={inputId} className="flex items-center gap-2 text-sm font-medium text-slate-700">
        {icon}
        {field.label}
        {field.required && <span className="text-red-500">*</span>}
      </label>

      {field.type === 'textarea' ? (
        <textarea
          id={inputId}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
          rows={3}
          className={cn(baseInputClasses, "resize-none")}
        />
      ) : field.type === 'select' ? (
        <select
          id={inputId}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={baseInputClasses}
        >
          <option value="">请选择</option>
          {field.options?.map(opt => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      ) : (
        <input
          id={inputId}
          type={field.type === 'date' ? 'date' : 'text'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
          className={baseInputClasses}
        />
      )}

      {error && (
        <p className="text-xs text-red-500 flex items-center gap-1">
          <AlertCircle className="w-3 h-3" />
          {error}
        </p>
      )}
    </div>
  );
}
