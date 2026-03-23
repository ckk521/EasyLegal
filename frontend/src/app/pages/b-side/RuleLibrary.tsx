/**
 * 规则库管理页面 - 模板、字段定义、文档管理
 */
import { useState, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import {
  Plus, Upload, Trash2, Edit2, FileText, Database, Loader2,
  FileCheck, AlertCircle, ChevronRight, Save, X, BookOpen
} from 'lucide-react';
import {
  documentApi,
  TemplateItem,
  FieldDefinitionItem,
  DocumentItem
} from '../../services/api';

type TabType = 'templates' | 'fields' | 'documents';

export function RuleLibrary() {
  const [activeTab, setActiveTab] = useState<TabType>('templates');

  const tabs = [
    { key: 'templates' as TabType, label: '合同模板', icon: FileText },
    { key: 'fields' as TabType, label: '字段定义', icon: Database },
    { key: 'documents' as TabType, label: '知识文档', icon: BookOpen },
  ];

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">规则库管理</h2>
        <p className="text-sm text-slate-500">管理合同模板、字段定义和知识文档</p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-slate-200">
        <nav className="flex gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 pb-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm">
        {activeTab === 'templates' && <TemplatesSection />}
        {activeTab === 'fields' && <FieldDefinitionsSection />}
        {activeTab === 'documents' && <DocumentsSection />}
      </div>
    </div>
  );
}

// ==================== 模板管理 ====================

function TemplatesSection() {
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    setIsLoading(true);
    try {
      const data = await documentApi.getTemplates();
      setTemplates(data);
    } catch (error) {
      console.error('加载模板失败:', error);
    }
    setIsLoading(false);
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const name = file.name.replace(/\.[^/.]+$/, '');
    const contractType = '租赁合同'; // 默认

    setIsLoading(true);
    try {
      await documentApi.uploadTemplate(file, name, contractType);
      toast.success('模板上传成功');
      loadTemplates();
      setShowUpload(false);
    } catch (error: any) {
      toast.error('上传失败: ' + error.message);
    }
    setIsLoading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除此模板吗？')) return;

    try {
      await documentApi.deleteTemplate(id);
      toast.success('删除成功');
      loadTemplates();
    } catch (error: any) {
      toast.error('删除失败: ' + error.message);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-sm text-slate-600">上传合同模板供智能体使用，支持 PDF、Word、Markdown 格式</p>
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Upload className="w-4 h-4" />
          上传模板
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.doc,.md,.txt"
          className="hidden"
          onChange={handleUpload}
        />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
        </div>
      ) : templates.length === 0 ? (
        <div className="text-center py-12 bg-slate-50 rounded-lg">
          <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500">暂无模板</p>
          <p className="text-sm text-slate-400 mt-1">点击上方按钮上传合同模板</p>
        </div>
      ) : (
        <div className="space-y-3">
          {templates.map((template) => (
            <div key={template.id} className="flex items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center">
                  <FileText className="w-5 h-5 text-indigo-600" />
                </div>
                <div>
                  <h4 className="font-medium text-slate-900">{template.name}</h4>
                  <p className="text-sm text-slate-500">{template.contract_type} · {template.file_type.toUpperCase()}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${template.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                  {template.is_active ? '已启用' : '已禁用'}
                </span>
                <button
                  onClick={() => handleDelete(template.id)}
                  className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ==================== 字段定义管理 ====================

function FieldDefinitionsSection() {
  const [definitions, setDefinitions] = useState<FieldDefinitionItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editFields, setEditFields] = useState('');

  useEffect(() => {
    loadDefinitions();
  }, []);

  const loadDefinitions = async () => {
    setIsLoading(true);
    try {
      const data = await documentApi.getFieldDefinitions();
      setDefinitions(data);
    } catch (error) {
      console.error('加载字段定义失败:', error);
    }
    setIsLoading(false);
  };

  const handleInitLease = async () => {
    setIsLoading(true);
    try {
      await documentApi.initLeaseFieldDefinition();
      toast.success('初始化成功');
      loadDefinitions();
    } catch (error: any) {
      toast.error('初始化失败: ' + error.message);
    }
    setIsLoading(false);
  };

  const handleSaveFields = async (id: number) => {
    try {
      await documentApi.updateFieldDefinition(id, { fields: editFields });
      toast.success('保存成功');
      setEditingId(null);
      loadDefinitions();
    } catch (error: any) {
      toast.error('保存失败: ' + error.message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除此字段定义吗？')) return;

    try {
      await documentApi.deleteFieldDefinition(id);
      toast.success('删除成功');
      loadDefinitions();
    } catch (error: any) {
      toast.error('删除失败: ' + error.message);
    }
  };

  const parseFields = (fieldsJson: string) => {
    try {
      return JSON.parse(fieldsJson);
    } catch {
      return [];
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-sm text-slate-600">定义合同生成时需要收集的字段信息</p>
        <button
          onClick={handleInitLease}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50"
        >
          <Plus className="w-4 h-4" />
          初始化租赁合同字段
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
        </div>
      ) : definitions.length === 0 ? (
        <div className="text-center py-12 bg-slate-50 rounded-lg">
          <Database className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500">暂无字段定义</p>
          <p className="text-sm text-slate-400 mt-1">点击上方按钮初始化预置字段定义</p>
        </div>
      ) : (
        <div className="space-y-4">
          {definitions.map((def) => (
            <div key={def.id} className="border border-slate-200 rounded-lg overflow-hidden">
              <div className="flex items-center justify-between p-4 bg-slate-50 border-b border-slate-200">
                <div className="flex items-center gap-3">
                  <Database className="w-5 h-5 text-indigo-600" />
                  <div>
                    <h4 className="font-medium text-slate-900">{def.name}</h4>
                    <p className="text-sm text-slate-500">{def.contract_type}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setEditingId(editingId === def.id ? null : def.id);
                      setEditFields(def.fields);
                    }}
                    className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(def.id)}
                    className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {editingId === def.id ? (
                <div className="p-4 space-y-3">
                  <textarea
                    value={editFields}
                    onChange={(e) => setEditFields(e.target.value)}
                    className="w-full h-64 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm font-mono focus:ring-2 focus:ring-indigo-500 resize-none"
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => setEditingId(null)}
                      className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-200"
                    >
                      取消
                    </button>
                    <button
                      onClick={() => handleSaveFields(def.id)}
                      className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700"
                    >
                      <Save className="w-4 h-4" />
                      保存
                    </button>
                  </div>
                </div>
              ) : (
                <div className="p-4">
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                    {parseFields(def.fields).map((field: any, i: number) => (
                      <div key={i} className="px-3 py-2 bg-slate-50 rounded-lg">
                        <p className="text-sm font-medium text-slate-900">{field.label}</p>
                        <p className="text-xs text-slate-500">{field.name} · {field.type}</p>
                        {field.required && (
                          <span className="text-xs text-red-500">必填</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ==================== 文档管理 ====================

function DocumentsSection() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    setIsLoading(true);
    try {
      const data = await documentApi.getDocuments();
      setDocuments(data.items);
    } catch (error) {
      console.error('加载文档失败:', error);
    }
    setIsLoading(false);
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsLoading(true);
    try {
      await documentApi.uploadDocument(file, 'other', file.name);
      toast.success('文档上传成功');
      loadDocuments();
    } catch (error: any) {
      toast.error('上传失败: ' + error.message);
    }
    setIsLoading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleIndex = async (id: number) => {
    try {
      const result = await documentApi.indexDocument(id);
      toast.success(`索引成功，共 ${result.chunk_count} 个文档块`);
      loadDocuments();
    } catch (error: any) {
      toast.error('索引失败: ' + error.message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除此文档吗？')) return;

    try {
      await documentApi.deleteDocument(id);
      toast.success('删除成功');
      loadDocuments();
    } catch (error: any) {
      toast.error('删除失败: ' + error.message);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-sm text-slate-600">上传知识文档到向量库，用于 RAG 检索增强</p>
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Upload className="w-4 h-4" />
          上传文档
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.doc,.md,.txt"
          className="hidden"
          onChange={handleUpload}
        />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
        </div>
      ) : documents.length === 0 ? (
        <div className="text-center py-12 bg-slate-50 rounded-lg">
          <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500">暂无文档</p>
          <p className="text-sm text-slate-400 mt-1">点击上方按钮上传知识文档</p>
        </div>
      ) : (
        <div className="space-y-3">
          {documents.map((doc) => (
            <div key={doc.id} className="flex items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center">
                  <FileCheck className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <h4 className="font-medium text-slate-900">{doc.name}</h4>
                  <p className="text-sm text-slate-500">
                    {doc.file_type.toUpperCase()} · {doc.chunk_count} 个文档块
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${doc.is_indexed ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                  {doc.is_indexed ? '已索引' : '待索引'}
                </span>
                {!doc.is_indexed && (
                  <button
                    onClick={() => handleIndex(doc.id)}
                    className="px-3 py-1.5 text-xs font-medium text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                  >
                    索引
                  </button>
                )}
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
