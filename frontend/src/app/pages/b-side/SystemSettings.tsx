/**
 * 系统配置页面 - Tab布局
 */
import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { Loader2, CheckCircle, XCircle, Eye, EyeOff, Save, RefreshCw, Plus, Trash2, Edit2 } from 'lucide-react';
import {
  configApi,
  LLMConfigInput,
  LLMVerifyResult,
  LegalScopeConfig,
  LegalScopeConfigInput,
  RejectScriptConfig,
  RejectScriptConfigInput,
  IntentConfig,
  IntentConfigInput
} from '../../services/api';

type ConfigTab = 'model' | 'dialog' | 'security';

export function SystemSettings() {
  const [activeTab, setActiveTab] = useState<ConfigTab>('model');

  const tabs = [
    { key: 'model' as ConfigTab, label: '模型配置' },
    { key: 'dialog' as ConfigTab, label: '对话配置' },
    { key: 'security' as ConfigTab, label: '安全配置' },
  ];

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">系统配置</h2>
        <p className="text-sm text-slate-500">管理平台模型参数、对话策略与安全设置</p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-slate-200">
        <nav className="flex gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm">
        {activeTab === 'model' && <ModelConfigTab />}
        {activeTab === 'dialog' && <DialogConfigTab />}
        {activeTab === 'security' && <SecurityConfigTab />}
      </div>
    </div>
  );
}

// ==================== 模型配置 Tab ====================

function ModelConfigTab() {
  const [llmConfig, setLLMConfig] = useState<LLMConfigInput>({
    name: 'default',
    api_key: '',
    base_url: '',
    model_name: '',
    api_type: 'openai-completions',
    is_active: true,
  });
  const [embeddingConfig, setEmbeddingConfig] = useState({
    model_name: 'm3e-base',
    chunk_size: 512,
    chunk_overlap: 50,
  });
  const [showApiKey, setShowApiKey] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<LLMVerifyResult | null>(null);
  const [hasExistingConfig, setHasExistingConfig] = useState(false);

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    setIsLoading(true);
    try {
      // 加载LLM配置
      const llm = await configApi.getLLMConfig();
      setLLMConfig({
        name: llm.name,
        api_key: llm.api_key,
        base_url: llm.base_url,
        model_name: llm.model_name,
        api_type: llm.api_type,
        is_active: llm.is_active,
      });
      setHasExistingConfig(true);
    } catch (error: any) {
      if (error.message?.includes('尚未配置')) {
        setHasExistingConfig(false);
      }
    }

    try {
      // 加载Embedding配置
      const emb = await configApi.getEmbeddingConfig();
      setEmbeddingConfig({
        model_name: emb.model_name,
        chunk_size: emb.chunk_size,
        chunk_overlap: emb.chunk_overlap,
      });
    } catch (error) {
      console.error('加载Embedding配置失败:', error);
    }
    setIsLoading(false);
  };

  const handleVerify = async () => {
    if (!llmConfig.api_key || !llmConfig.base_url || !llmConfig.model_name) {
      toast.error('请填写完整的API配置信息');
      return;
    }

    setIsVerifying(true);
    setVerifyResult(null);

    try {
      const result = await configApi.verifyLLMConfig(llmConfig);
      setVerifyResult(result);

      if (result.success) {
        toast.success(result.message);
      } else {
        toast.error(result.message);
      }
    } catch (error: any) {
      toast.error('验证失败: ' + error.message);
      setVerifyResult({ success: false, message: error.message });
    }
    setIsVerifying(false);
  };

  const handleSave = async () => {
    if (!verifyResult?.success) {
      toast.error('请先验证配置');
      return;
    }

    setIsLoading(true);
    try {
      await configApi.verifyAndSaveLLMConfig(llmConfig);
      toast.success('大模型配置保存成功');
      setHasExistingConfig(true);
    } catch (error: any) {
      toast.error('保存失败: ' + error.message);
    }
    setIsLoading(false);
  };

  const handleSaveEmbedding = async () => {
    setIsLoading(true);
    try {
      await configApi.updateEmbeddingConfig(embeddingConfig);
      toast.success('Embedding配置保存成功');
    } catch (error: any) {
      toast.error('保存失败: ' + error.message);
    }
    setIsLoading(false);
  };

  if (isLoading && !hasExistingConfig) {
    return (
      <div className="p-8 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-8">
      {/* 大模型配置 */}
      <div className="space-y-4">
        <h3 className="font-semibold text-slate-900 flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-indigo-600 rounded-full" />
          大模型配置
          {hasExistingConfig && (
            <span className="text-xs font-normal text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
              已配置
            </span>
          )}
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-600">API 类型</label>
            <select
              value={llmConfig.api_type}
              onChange={(e) => setLLMConfig({ ...llmConfig, api_type: e.target.value })}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            >
              <option value="openai-completions">OpenAI Completions</option>
              <option value="openai-chat">OpenAI Chat</option>
              <option value="anthropic">Anthropic</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-600">配置名称</label>
            <input
              type="text"
              value={llmConfig.name}
              onChange={(e) => setLLMConfig({ ...llmConfig, name: e.target.value })}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              placeholder="default"
            />
          </div>

          <div className="space-y-2 md:col-span-2">
            <label className="text-xs font-medium text-slate-600">Base URL</label>
            <input
              type="text"
              value={llmConfig.base_url}
              onChange={(e) => setLLMConfig({ ...llmConfig, base_url: e.target.value })}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              placeholder="https://api.openai.com/v1"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-600">API Key</label>
            <div className="relative">
              <input
                type={showApiKey ? 'text' : 'password'}
                value={llmConfig.api_key}
                onChange={(e) => setLLMConfig({ ...llmConfig, api_key: e.target.value })}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent pr-10"
                placeholder="sk-..."
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-600">Model Name</label>
            <input
              type="text"
              value={llmConfig.model_name}
              onChange={(e) => setLLMConfig({ ...llmConfig, model_name: e.target.value })}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              placeholder="gpt-4, claude-3-opus, etc."
            />
          </div>
        </div>

        {/* 验证结果 */}
        {verifyResult && (
          <div className={`flex items-start gap-3 p-4 rounded-lg ${
            verifyResult.success ? 'bg-emerald-50 border border-emerald-200' : 'bg-red-50 border border-red-200'
          }`}>
            {verifyResult.success ? (
              <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <XCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            )}
            <div>
              <p className={`text-sm font-medium ${verifyResult.success ? 'text-emerald-800' : 'text-red-800'}`}>
                {verifyResult.message}
              </p>
              {verifyResult.model_info?.available_models && (
                <p className="text-xs text-slate-600 mt-1">
                  可用模型: {verifyResult.model_info.available_models.slice(0, 5).join(', ')}
                  {verifyResult.model_info.available_models.length > 5 && '...'}
                </p>
              )}
            </div>
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex gap-3 pt-2">
          <button
            onClick={handleVerify}
            disabled={isVerifying || !llmConfig.api_key || !llmConfig.base_url || !llmConfig.model_name}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-100 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isVerifying ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            验证连接
          </button>
          <button
            onClick={handleSave}
            disabled={!verifyResult?.success || isLoading}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            保存配置
          </button>
        </div>
      </div>

      {/* 分隔线 */}
      <div className="border-t border-slate-100" />

      {/* Embedding 配置 */}
      <div className="space-y-4">
        <h3 className="font-semibold text-slate-900 flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-indigo-600 rounded-full" />
          Embedding 配置
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-600">模型名称</label>
            <input
              type="text"
              value={embeddingConfig.model_name}
              onChange={(e) => setEmbeddingConfig({ ...embeddingConfig, model_name: e.target.value })}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-600">Chunk 大小</label>
            <input
              type="number"
              value={embeddingConfig.chunk_size}
              onChange={(e) => setEmbeddingConfig({ ...embeddingConfig, chunk_size: Number(e.target.value) })}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-600">重叠大小</label>
            <input
              type="number"
              value={embeddingConfig.chunk_overlap}
              onChange={(e) => setEmbeddingConfig({ ...embeddingConfig, chunk_overlap: Number(e.target.value) })}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <button
            onClick={handleSaveEmbedding}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Save className="w-4 h-4" />
            保存配置
          </button>
        </div>
      </div>
    </div>
  );
}

// ==================== 对话配置 Tab ====================

function DialogConfigTab() {
  const [activeSection, setActiveSection] = useState<'legal' | 'reject' | 'intent'>('legal');
  const [isLoading, setIsLoading] = useState(false);

  const sections = [
    { key: 'legal' as const, label: '法律范围' },
    { key: 'reject' as const, label: '拒绝话术' },
    { key: 'intent' as const, label: '核心意图' },
  ];

  return (
    <div className="p-6">
      {/* 子导航 */}
      <div className="flex gap-2 mb-6">
        {sections.map((section) => (
          <button
            key={section.key}
            onClick={() => setActiveSection(section.key)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeSection === section.key
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {section.label}
          </button>
        ))}
      </div>

      {/* 内容区域 */}
      {activeSection === 'legal' && <LegalScopeSection />}
      {activeSection === 'reject' && <RejectScriptSection />}
      {activeSection === 'intent' && <IntentSection />}
    </div>
  );
}

// 法律范围配置
function LegalScopeSection() {
  const [config, setConfig] = useState<LegalScopeConfigInput>({
    scope_description: '',
    allowed_topics: '',
    forbidden_topics: '',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [hasConfig, setHasConfig] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setIsLoading(true);
    try {
      const data = await configApi.getLegalScopeConfig();
      setConfig({
        name: data.name,
        scope_description: data.scope_description,
        allowed_topics: data.allowed_topics || '',
        forbidden_topics: data.forbidden_topics || '',
      });
      setHasConfig(true);
    } catch (error: any) {
      if (!error.message?.includes('尚未配置')) {
        console.error('加载配置失败:', error);
      }
      setHasConfig(false);
    }
    setIsLoading(false);
  };

  const handleSave = async () => {
    if (!config.scope_description.trim()) {
      toast.error('请填写法律范围描述');
      return;
    }

    setIsLoading(true);
    try {
      if (hasConfig) {
        await configApi.updateLegalScopeConfig(config);
      } else {
        await configApi.createLegalScopeConfig(config);
      }
      toast.success('法律范围配置保存成功');
      setHasConfig(true);
    } catch (error: any) {
      toast.error('保存失败: ' + error.message);
    }
    setIsLoading(false);
  };

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700">法律范围描述</label>
          <textarea
            value={config.scope_description}
            onChange={(e) => setConfig({ ...config, scope_description: e.target.value })}
            className="w-full h-32 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
            placeholder="描述智能体可以处理的法律问题范围，例如：本智能体专注于合同法、劳动法、知识产权法等领域的法律咨询服务..."
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700">允许的主题（每行一个）</label>
            <textarea
              value={config.allowed_topics || ''}
              onChange={(e) => setConfig({ ...config, allowed_topics: e.target.value })}
              className="w-full h-40 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
              placeholder="合同咨询&#10;劳动纠纷&#10;知识产权&#10;房产法律"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700">禁止的主题（每行一个）</label>
            <textarea
              value={config.forbidden_topics || ''}
              onChange={(e) => setConfig({ ...config, forbidden_topics: e.target.value })}
              className="w-full h-40 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
              placeholder="医疗诊断&#10;投资建议&#10;技术编程&#10;娱乐八卦"
            />
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          保存配置
        </button>
      </div>
    </div>
  );
}

// 拒绝话术配置
function RejectScriptSection() {
  const [config, setConfig] = useState<RejectScriptConfigInput>({
    rejection_message: '',
    redirect_template: '',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [hasConfig, setHasConfig] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setIsLoading(true);
    try {
      const data = await configApi.getRejectScriptConfig();
      setConfig({
        name: data.name,
        rejection_message: data.rejection_message,
        redirect_template: data.redirect_template || '',
      });
      setHasConfig(true);
    } catch (error: any) {
      if (!error.message?.includes('尚未配置')) {
        console.error('加载配置失败:', error);
      }
      setHasConfig(false);
      // 设置默认值
      setConfig({
        rejection_message: '抱歉，我是一款法律咨询服务智能体，只能回答与法律相关的问题。如有法律问题，我很乐意为您解答。',
        redirect_template: '如果您有法律方面的问题，比如{examples}等，我很乐意为您提供专业建议。',
      });
    }
    setIsLoading(false);
  };

  const handleSave = async () => {
    if (!config.rejection_message.trim()) {
      toast.error('请填写拒绝话术');
      return;
    }

    setIsLoading(true);
    try {
      if (hasConfig) {
        await configApi.updateRejectScriptConfig(config);
      } else {
        await configApi.createRejectScriptConfig(config);
      }
      toast.success('拒绝话术配置保存成功');
      setHasConfig(true);
    } catch (error: any) {
      toast.error('保存失败: ' + error.message);
    }
    setIsLoading(false);
  };

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700">
            拒绝话术
            <span className="text-red-500 ml-1">*</span>
          </label>
          <textarea
            value={config.rejection_message}
            onChange={(e) => setConfig({ ...config, rejection_message: e.target.value })}
            className="w-full h-32 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
            placeholder="当用户提出非法律问题时的回复，例如：抱歉，我是一款法律咨询服务智能体，只能回答与法律相关的问题..."
          />
          <p className="text-xs text-slate-500">
            此话术会在智能体识别到用户问题不属于法律范畴时自动返回
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700">引导话术模板（可选）</label>
          <textarea
            value={config.redirect_template || ''}
            onChange={(e) => setConfig({ ...config, redirect_template: e.target.value })}
            className="w-full h-20 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
            placeholder="引导用户回到法律话题的模板，可使用{examples}占位符..."
          />
          <p className="text-xs text-slate-500">提示：使用 {'{examples}'} 作为法律问题示例的占位符</p>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          保存配置
        </button>
      </div>
    </div>
  );
}

// 核心意图配置
function IntentSection() {
  const [intents, setIntents] = useState<IntentConfig[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [editingIntent, setEditingIntent] = useState<IntentConfig | null>(null);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    loadIntents();
  }, []);

  const loadIntents = async () => {
    setIsLoading(true);
    try {
      const data = await configApi.getIntentConfigs();
      setIntents(data);
    } catch (error) {
      console.error('加载意图配置失败:', error);
    }
    setIsLoading(false);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除此意图配置吗？')) return;

    try {
      await configApi.deleteIntentConfig(id);
      toast.success('删除成功');
      loadIntents();
    } catch (error: any) {
      toast.error('删除失败: ' + error.message);
    }
  };

  const handleEdit = (intent: IntentConfig) => {
    setEditingIntent(intent);
    setShowForm(true);
  };

  const handleFormClose = () => {
    setShowForm(false);
    setEditingIntent(null);
  };

  const handleFormSave = () => {
    handleFormClose();
    loadIntents();
  };

  return (
    <div className="space-y-4">
      {/* 头部 */}
      <div className="flex justify-between items-center">
        <p className="text-sm text-slate-600">配置智能体可识别的核心意图，优先级越高越优先匹配</p>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-3 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          添加意图
        </button>
      </div>

      {/* 意图列表 */}
      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
        </div>
      ) : intents.length === 0 ? (
        <div className="text-center py-12 bg-slate-50 rounded-lg">
          <p className="text-slate-500">暂无意图配置</p>
          <p className="text-sm text-slate-400 mt-1">点击上方"添加意图"按钮创建新配置</p>
        </div>
      ) : (
        <div className="space-y-3">
          {intents.map((intent) => (
            <div key={intent.id} className="flex items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <h4 className="font-medium text-slate-900">{intent.name}</h4>
                  <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs rounded">
                    优先级: {intent.priority}
                  </span>
                </div>
                {intent.description && (
                  <p className="text-sm text-slate-600 mt-1">{intent.description}</p>
                )}
                {intent.trigger_words && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {JSON.parse(intent.trigger_words).slice(0, 5).map((word: string, i: number) => (
                      <span key={i} className="px-2 py-0.5 bg-slate-200 text-slate-600 text-xs rounded">
                        {word}
                      </span>
                    ))}
                    {JSON.parse(intent.trigger_words).length > 5 && (
                      <span className="text-xs text-slate-400">+{JSON.parse(intent.trigger_words).length - 5}</span>
                    )}
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleEdit(intent)}
                  className="p-2 text-slate-400 hover:text-indigo-600 transition-colors"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDelete(intent.id)}
                  className="p-2 text-slate-400 hover:text-red-600 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 编辑表单弹窗 */}
      {showForm && (
        <IntentFormModal
          intent={editingIntent}
          onClose={handleFormClose}
          onSave={handleFormSave}
        />
      )}
    </div>
  );
}

// 意图表单弹窗
function IntentFormModal({ intent, onClose, onSave }: {
  intent: IntentConfig | null;
  onClose: () => void;
  onSave: () => void;
}) {
  const [formData, setFormData] = useState<IntentConfigInput>({
    name: intent?.name || '',
    description: intent?.description || '',
    trigger_words: intent?.trigger_words || '[]',
    response_template: intent?.response_template || '',
    priority: intent?.priority || 0,
    is_active: intent?.is_active ?? true,
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleSave = async () => {
    if (!formData.name.trim()) {
      toast.error('请填写意图名称');
      return;
    }

    setIsLoading(true);
    try {
      if (intent) {
        await configApi.updateIntentConfig(intent.id, formData);
      } else {
        await configApi.createIntentConfig(formData);
      }
      toast.success(intent ? '更新成功' : '创建成功');
      onSave();
    } catch (error: any) {
      toast.error('保存失败: ' + error.message);
    }
    setIsLoading(false);
  };

  // 解析触发词用于显示
  const triggerWords = formData.trigger_words ? JSON.parse(formData.trigger_words) : [];
  const [triggerInput, setTriggerInput] = useState(triggerWords.join('\n'));

  const handleTriggerChange = (value: string) => {
    setTriggerInput(value);
    const words = value.split('\n').filter(w => w.trim());
    setFormData({ ...formData, trigger_words: JSON.stringify(words) });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">
            {intent ? '编辑意图' : '添加意图'}
          </h3>

          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">意图名称 *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500"
                placeholder="例如：合同生成"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">描述</label>
              <textarea
                value={formData.description || ''}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full h-20 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 resize-none"
                placeholder="描述此意图的用途..."
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">触发词（每行一个）</label>
              <textarea
                value={triggerInput}
                onChange={(e) => handleTriggerChange(e.target.value)}
                className="w-full h-28 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 resize-none"
                placeholder="生成合同&#10;起草合同&#10;我要签合同"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">优先级</label>
              <input
                type="number"
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: Number(e.target.value) })}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500"
                min="0"
                max="100"
              />
              <p className="text-xs text-slate-500">数字越大优先级越高，范围 0-100</p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">响应模板</label>
              <textarea
                value={formData.response_template || ''}
                onChange={(e) => setFormData({ ...formData, response_template: e.target.value })}
                className="w-full h-24 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 resize-none"
                placeholder="当识别到此意图时的回复模板..."
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button
              onClick={onClose}
              className="px-4 py-2.5 bg-slate-100 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-200 transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleSave}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              保存
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==================== 安全配置 Tab ====================

function SecurityConfigTab() {
  return (
    <div className="p-6">
      <div className="text-center py-12">
        <p className="text-slate-500">安全配置功能开发中...</p>
        <p className="text-sm text-slate-400 mt-2">包含：敏感信息配置</p>
      </div>
    </div>
  );
}
