/**
 * API 服务层 - 与后端交互
 */

const API_BASE_URL = 'http://localhost:8000';

interface ApiResponse<T> {
  success?: boolean;
  message?: string;
  detail?: string;
  data?: T;
}

// C端用户相关
export interface User {
  id: number;
  username: string;
  nickname: string | null;
  status: string;
  created_at: string;
  last_login_at: string | null;
}

export interface LoginResponse {
  token: string;
  token_type: string;
  user: User;
}

export interface RegisterResponse {
  user_id: number;
  message: string;
}

// B端员工相关
export interface Staff {
  id: number;
  username: string;
  nickname: string | null;
  role: 'admin' | 'operator' | 'viewer';
  status: string;
  first_login: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface StaffLoginResponse {
  token: string;
  token_type: string;
  staff: Staff;
  first_login: boolean;
}

// API 请求封装
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // 根据路由选择正确的token
  // B端API使用 staff_token，C端API使用 user_token
  let token: string | null = null;
  if (endpoint.startsWith('/api/admin') || endpoint.startsWith('/api/staff')) {
    token = localStorage.getItem('staff_token');
  } else if (endpoint.startsWith('/api/auth') || endpoint.startsWith('/api/chat') || endpoint.startsWith('/api/contract')) {
    token = localStorage.getItem('user_token');
  } else {
    // 默认使用 user_token（C端用户）
    token = localStorage.getItem('user_token');
  }

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const data = await response.json();

  if (!response.ok) {
    // 处理不同类型的错误响应
    let errorMsg = '请求失败';
    if (typeof data.detail === 'string') {
      errorMsg = data.detail;
    } else if (data.detail && typeof data.detail === 'object') {
      // Pydantic验证错误
      errorMsg = JSON.stringify(data.detail);
    }
    throw new Error(errorMsg);
  }

  return data;
}

// ==================== C端用户 API ====================

export const userApi = {
  // 用户注册
  register: async (username: string, password: string, nickname?: string): Promise<RegisterResponse> => {
    return request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password, nickname }),
    });
  },

  // 用户登录
  login: async (username: string, password: string): Promise<LoginResponse> => {
    return request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  },

  // 用户登出
  logout: async (): Promise<ApiResponse<null>> => {
    return request('/api/auth/logout', { method: 'POST' });
  },

  // 获取当前用户信息
  getMe: async (): Promise<User> => {
    return request('/api/auth/me');
  },

  // 修改密码
  changePassword: async (oldPassword: string, newPassword: string): Promise<ApiResponse<null>> => {
    return request('/api/auth/password', {
      method: 'PUT',
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
  },

  // 修改昵称
  updateNickname: async (nickname: string): Promise<User> => {
    return request(`/api/auth/nickname?nickname=${encodeURIComponent(nickname)}`, {
      method: 'PUT',
    });
  },
};

// ==================== B端员工 API ====================

export const staffApi = {
  // 员工登录
  login: async (username: string, password: string): Promise<StaffLoginResponse> => {
    return request('/api/staff/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  },

  // 员工登出
  logout: async (): Promise<ApiResponse<null>> => {
    return request('/api/staff/auth/logout', { method: 'POST' });
  },

  // 获取当前员工信息
  getMe: async (): Promise<Staff> => {
    return request('/api/staff/auth/me');
  },

  // 修改密码
  changePassword: async (oldPassword: string, newPassword: string): Promise<ApiResponse<null>> => {
    return request('/api/staff/auth/password', {
      method: 'PUT',
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
  },
};

// ==================== B端管理 API ====================

export const adminApi = {
  // 获取用户列表
  getUsers: async (params?: { status?: string; skip?: number; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));

    const query = searchParams.toString();
    return request<{ total: number; items: User[] }>(`/api/admin/users${query ? `?${query}` : ''}`);
  },

  // 获取用户详情
  getUser: async (userId: number): Promise<User> => {
    return request(`/api/admin/users/${userId}`);
  },

  // 更新用户状态
  updateUserStatus: async (userId: number, status: string): Promise<ApiResponse<null>> => {
    return request(`/api/admin/users/${userId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    });
  },

  // 删除用户
  deleteUser: async (userId: number): Promise<ApiResponse<null>> => {
    return request(`/api/admin/users/${userId}`, { method: 'DELETE' });
  },

  // 获取员工列表
  getStaff: async (params?: { role?: string; status?: string; skip?: number; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.role) searchParams.set('role', params.role);
    if (params?.status) searchParams.set('status', params.status);
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));

    const query = searchParams.toString();
    return request<{ total: number; items: Staff[] }>(`/api/admin/staff${query ? `?${query}` : ''}`);
  },

  // 创建员工
  createStaff: async (data: { username: string; password: string; nickname?: string; role?: string }): Promise<Staff> => {
    return request('/api/admin/staff', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // 获取员工详情
  getStaffDetail: async (staffId: number): Promise<Staff> => {
    return request(`/api/admin/staff/${staffId}`);
  },

  // 更新员工状态
  updateStaffStatus: async (staffId: number, status: string): Promise<ApiResponse<null>> => {
    return request(`/api/admin/staff/${staffId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    });
  },

  // 删除员工
  deleteStaff: async (staffId: number): Promise<ApiResponse<null>> => {
    return request(`/api/admin/staff/${staffId}`, { method: 'DELETE' });
  },

  // 获取仪表盘统计
  getDashboardStats: async () => {
    return request<{
      users: { total: number; active: number };
      staff: { total: number; admin_count: number };
    }>('/api/admin/dashboard/stats');
  },
};

// ==================== 配置管理 API ====================

export interface LLMConfig {
  id: number;
  name: string;
  api_key: string;
  base_url: string;
  model_name: string;
  api_type: string;
  is_active: boolean;
  last_verified_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LLMConfigInput {
  name?: string;
  api_key: string;
  base_url: string;
  model_name: string;
  api_type?: string;
  is_active?: boolean;
}

export interface LLMVerifyResult {
  success: boolean;
  message: string;
  model_info?: {
    available_models?: string[];
    configured_model_available?: boolean;
  };
}

export interface EmbeddingConfig {
  id: number;
  name: string;
  model_name: string;
  chunk_size: number;
  chunk_overlap: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmbeddingConfigInput {
  name?: string;
  model_name?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  is_active?: boolean;
}

// 法律范围配置
export interface LegalScopeConfig {
  id: number;
  name: string;
  scope_description: string;
  allowed_topics: string | null;
  forbidden_topics: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LegalScopeConfigInput {
  name?: string;
  scope_description: string;
  allowed_topics?: string;
  forbidden_topics?: string;
  is_active?: boolean;
}

// 拒绝话术配置
export interface RejectScriptConfig {
  id: number;
  name: string;
  rejection_message: string;
  redirect_template: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RejectScriptConfigInput {
  name?: string;
  rejection_message: string;
  redirect_template?: string;
  is_active?: boolean;
}

// 核心意图配置
export interface IntentConfig {
  id: number;
  name: string;
  description: string | null;
  trigger_words: string | null;
  response_template: string | null;
  priority: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface IntentConfigInput {
  name: string;
  description?: string;
  trigger_words?: string;
  response_template?: string;
  priority?: number;
  is_active?: boolean;
}

export const configApi = {
  // 获取当前激活的LLM配置
  getLLMConfig: async (): Promise<LLMConfig> => {
    return request('/api/admin/config/llm');
  },

  // 获取所有LLM配置列表
  listLLMConfigs: async (): Promise<LLMConfig[]> => {
    return request('/api/admin/config/llm/list');
  },

  // 创建LLM配置
  createLLMConfig: async (data: LLMConfigInput): Promise<LLMConfig> => {
    return request('/api/admin/config/llm', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // 获取指定LLM配置
  getLLMConfigById: async (id: number): Promise<LLMConfig> => {
    return request(`/api/admin/config/llm/${id}`);
  },

  // 更新指定LLM配置
  updateLLMConfigById: async (id: number, data: Partial<LLMConfigInput>): Promise<LLMConfig> => {
    return request(`/api/admin/config/llm/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // 激活指定LLM配置
  activateLLMConfig: async (id: number): Promise<{ message: string; config: LLMConfig }> => {
    return request(`/api/admin/config/llm/${id}/activate`, {
      method: 'PUT',
    });
  },

  // 删除指定LLM配置
  deleteLLMConfig: async (id: number): Promise<{ message: string }> => {
    return request(`/api/admin/config/llm/${id}`, {
      method: 'DELETE',
    });
  },

  // 初始化默认LLM配置
  initDefaultLLMConfigs: async (): Promise<{ message: string; created: string[]; skipped: string[] }> => {
    return request('/api/admin/config/llm/init-defaults', {
      method: 'POST',
    });
  },

  // 更新LLM配置（兼容旧API）
  updateLLMConfig: async (data: Partial<LLMConfigInput>): Promise<LLMConfig> => {
    return request('/api/admin/config/llm', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // 验证LLM配置
  verifyLLMConfig: async (data: LLMConfigInput): Promise<LLMVerifyResult> => {
    return request('/api/admin/config/llm/verify', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // 验证并保存LLM配置
  verifyAndSaveLLMConfig: async (data: LLMConfigInput): Promise<LLMConfig> => {
    return request('/api/admin/config/llm/verify-and-save', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // 获取Embedding配置
  getEmbeddingConfig: async (): Promise<EmbeddingConfig> => {
    return request('/api/admin/config/embedding');
  },

  // 更新Embedding配置
  updateEmbeddingConfig: async (data: Partial<EmbeddingConfigInput>): Promise<EmbeddingConfig> => {
    return request('/api/admin/config/embedding', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // 获取法律范围配置
  getLegalScopeConfig: async (): Promise<LegalScopeConfig> => {
    return request('/api/admin/config/legal-scope');
  },

  // 创建法律范围配置
  createLegalScopeConfig: async (data: LegalScopeConfigInput): Promise<LegalScopeConfig> => {
    return request('/api/admin/config/legal-scope', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // 更新法律范围配置
  updateLegalScopeConfig: async (data: Partial<LegalScopeConfigInput>): Promise<LegalScopeConfig> => {
    return request('/api/admin/config/legal-scope', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // 获取拒绝话术配置
  getRejectScriptConfig: async (): Promise<RejectScriptConfig> => {
    return request('/api/admin/config/reject-script');
  },

  // 创建拒绝话术配置
  createRejectScriptConfig: async (data: RejectScriptConfigInput): Promise<RejectScriptConfig> => {
    return request('/api/admin/config/reject-script', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // 更新拒绝话术配置
  updateRejectScriptConfig: async (data: Partial<RejectScriptConfigInput>): Promise<RejectScriptConfig> => {
    return request('/api/admin/config/reject-script', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // 获取所有核心意图配置
  getIntentConfigs: async (): Promise<IntentConfig[]> => {
    return request('/api/admin/config/intents');
  },

  // 获取单个核心意图配置
  getIntentConfig: async (id: number): Promise<IntentConfig> => {
    return request(`/api/admin/config/intents/${id}`);
  },

  // 创建核心意图配置
  createIntentConfig: async (data: IntentConfigInput): Promise<IntentConfig> => {
    return request('/api/admin/config/intents', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // 更新核心意图配置
  updateIntentConfig: async (id: number, data: Partial<IntentConfigInput>): Promise<IntentConfig> => {
    return request(`/api/admin/config/intents/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // 删除核心意图配置
  deleteIntentConfig: async (id: number): Promise<void> => {
    return request(`/api/admin/config/intents/${id}`, {
      method: 'DELETE',
    });
  },
};

// ==================== 文档管理 API ====================

export interface DocumentItem {
  id: number;
  name: string;
  file_path: string;
  file_type: string;
  doc_type: string;
  content: string | null;
  chunk_count: number;
  is_indexed: boolean;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface TemplateItem {
  id: number;
  name: string;
  contract_type: string;
  file_path: string;
  file_type: string;
  content: string | null;
  content_html?: string | null;
  variables: string | null;
  field_definition_id: number | null;
  is_active: boolean;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface FieldDefinitionItem {
  id: number;
  name: string;
  contract_type: string;
  fields: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export const documentApi = {
  // 获取文档列表
  getDocuments: async (docType?: string): Promise<{ total: number; items: DocumentItem[] }> => {
    const query = docType ? `?doc_type=${docType}` : '';
    return request(`/api/admin/documents${query}`);
  },

  // 上传文档
  uploadDocument: async (file: File, docType: string, name?: string, description?: string): Promise<DocumentItem> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_type', docType);
    if (name) formData.append('name', name);
    if (description) formData.append('description', description);

    const response = await fetch(`${API_BASE_URL}/api/admin/documents/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('staff_token')}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '上传失败');
    }

    return response.json();
  },

  // 索引文档到向量库
  indexDocument: async (docId: number): Promise<{ message: string; chunk_count: number }> => {
    return request(`/api/admin/documents/${docId}/index`, { method: 'POST' });
  },

  // 删除文档
  deleteDocument: async (docId: number): Promise<void> => {
    return request(`/api/admin/documents/${docId}`, { method: 'DELETE' });
  },

  // 获取模板列表
  getTemplates: async (contractType?: string): Promise<TemplateItem[]> => {
    const query = contractType ? `?contract_type=${contractType}` : '';
    return request(`/api/admin/documents/templates${query}`);
  },

  // 上传模板
  uploadTemplate: async (file: File, name: string, contractType: string, description?: string): Promise<TemplateItem> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name);
    formData.append('contract_type', contractType);
    if (description) formData.append('description', description);

    const response = await fetch(`${API_BASE_URL}/api/admin/documents/templates/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('staff_token')}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '上传失败');
    }

    return response.json();
  },

  // 获取单个模板详情
  getTemplate: async (templateId: number): Promise<TemplateItem> => {
    return request(`/api/admin/documents/templates/${templateId}`);
  },

  // 删除模板
  deleteTemplate: async (templateId: number): Promise<void> => {
    return request(`/api/admin/documents/templates/${templateId}`, { method: 'DELETE' });
  },

  // 初始化默认模板
  initDefaultTemplates: async (): Promise<{ message: string; created: string[]; skipped: string[] }> => {
    return request('/api/admin/documents/templates/init-defaults', { method: 'POST' });
  },

  // 获取字段定义列表
  getFieldDefinitions: async (contractType?: string): Promise<FieldDefinitionItem[]> => {
    const query = contractType ? `?contract_type=${contractType}` : '';
    return request(`/api/admin/documents/field-definitions${query}`);
  },

  // 创建字段定义
  createFieldDefinition: async (data: { name: string; contract_type: string; fields: string }): Promise<FieldDefinitionItem> => {
    return request('/api/admin/documents/field-definitions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // 更新字段定义
  updateFieldDefinition: async (id: number, data: Partial<{ name: string; contract_type: string; fields: string }>): Promise<FieldDefinitionItem> => {
    return request(`/api/admin/documents/field-definitions/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // 删除字段定义
  deleteFieldDefinition: async (id: number): Promise<void> => {
    return request(`/api/admin/documents/field-definitions/${id}`, { method: 'DELETE' });
  },

  // 初始化租赁合同字段定义
  initLeaseFieldDefinition: async (): Promise<{ message: string; id: number }> => {
    return request('/api/admin/documents/field-definitions/init-lease', { method: 'POST' });
  },
};

// ==================== 合同草稿 API ====================

export interface ContractDraftItem {
  id: number;
  contract_no: string;
  contract_type: string;
  title: string | null;
  status: 'draft' | 'completed';
  field_values: Record<string, string>;
  fields_definition: Array<{
    name: string;
    label: string;
    type: string;
    required: boolean;
    placeholder?: string;
  }>;
  template_id: number | null;
  created_at: string;
  updated_at: string;
}

export const contractDraftApi = {
  // 获取用户所有草稿/合同列表
  listDrafts: async (): Promise<ContractDraftItem[]> => {
    return request('/api/contract-drafts/list');
  },

  // 获取待处理的草稿（最新未完成）
  getPendingDraft: async (): Promise<ContractDraftItem | null> => {
    return request('/api/contract-drafts/pending');
  },

  // 获取单个草稿详情
  getDraft: async (draftId: number): Promise<ContractDraftItem> => {
    return request(`/api/contract-drafts/${draftId}`);
  },

  // 创建草稿
  createDraft: async (data: { contract_type: string; field_values?: Record<string, string> }): Promise<ContractDraftItem> => {
    return request('/api/contract-drafts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // 更新草稿（自动保存）
  updateDraft: async (draftId: number, fieldValues: Record<string, string>): Promise<ContractDraftItem> => {
    return request(`/api/contract-drafts/${draftId}`, {
      method: 'PUT',
      body: JSON.stringify({ field_values: fieldValues }),
    });
  },

  // 完成草稿
  completeDraft: async (draftId: number): Promise<{ message: string; contract_id: number; contract_no: string }> => {
    return request(`/api/contract-drafts/${draftId}/complete`, { method: 'POST' });
  },

  // 删除草稿
  deleteDraft: async (draftId: number): Promise<{ message: string }> => {
    return request(`/api/contract-drafts/${draftId}`, { method: 'DELETE' });
  },

  // 获取可用的合同类型
  getContractTypes: async (): Promise<Array<{
    contract_type: string;
    name: string;
    has_template: boolean;
    has_field_definition: boolean;
  }>> => {
    return request('/api/contract-drafts/types');
  },

  // 获取合同详情内容
  getContractContent: async (contractId: number): Promise<{
    id: number;
    contract_no: string;
    contract_type: string;
    title: string | null;
    status: string;
    content: string;
    field_values: Record<string, string>;
    created_at: string;
    updated_at: string;
  }> => {
    return request(`/api/contract-drafts/${contractId}/content`);
  },

  // 导出合同 (仅支持PDF)
  exportContract: async (contractId: number, format: string = 'pdf'): Promise<Blob> => {
    const token = localStorage.getItem('user_token');
    const response = await fetch(`${API_BASE_URL}/api/contract-drafts/${contractId}/export?format=${format}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '导出失败');
    }

    return response.blob();
  },
};

// ==================== 合同配置管理 API ====================

export interface ContractCategory {
  id: number;
  code: string;
  name: string;
  description: string | null;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface FieldLibraryItem {
  id: number;
  code: string;
  name: string;
  field_type: string;
  category_id: number | null;
  validation_rule: string | null;
  default_value: string | null;
  description: string | null;
  options: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  category?: ContractCategory | null;
}

export interface TemplateUploadResult {
  success: boolean;
  template_id?: number;
  template_name?: string;
  content_text?: string;
  content_html?: string;
  variables?: Array<{
    text: string;
    position: number;
    full_match: string;
    field_id: number | null;
    field_name: string | null;
    confidence: number;
  }>;
  blanks?: Array<{
    context: string;
    position: number;
    length: number;
    label: string;  // 自动提取的字段名
    field_id: number | null;
    field_name: string | null;
    confidence: number;
  }>;
  variable_count?: number;
  blank_count?: number;
  errors?: string[];
}

export const contractConfigApi = {
  // 获取合同类型列表
  getCategories: async (includeInactive = false): Promise<ContractCategory[]> => {
    return request(`/api/admin/contract-categories?include_inactive=${includeInactive}`);
  },

  // 创建合同类型
  createCategory: async (data: {
    code: string;
    name: string;
    description?: string;
    sort_order?: number;
  }): Promise<ContractCategory> => {
    return request('/api/admin/contract-categories', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // 更新合同类型
  updateCategory: async (id: number, data: Partial<{
    name: string;
    description: string;
    sort_order: number;
    is_active: boolean;
  }>): Promise<ContractCategory> => {
    return request(`/api/admin/contract-categories/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // 删除合同类型
  deleteCategory: async (id: number): Promise<{ message: string }> => {
    return request(`/api/admin/contract-categories/${id}`, { method: 'DELETE' });
  },

  // 初始化预设数据
  initDefaultData: async (): Promise<{
    message: string;
    created_categories: number;
    created_fields: number;
  }> => {
    return request('/api/admin/contract-categories/init-default', { method: 'POST' });
  },

  // 获取字段库列表
  getFields: async (params?: {
    category_id?: number;
    include_universal?: boolean;
    include_inactive?: boolean;
  }): Promise<FieldLibraryItem[]> => {
    const searchParams = new URLSearchParams();
    if (params?.category_id !== undefined) {
      searchParams.set('category_id', String(params.category_id));
    }
    if (params?.include_universal !== undefined) {
      searchParams.set('include_universal', String(params.include_universal));
    }
    if (params?.include_inactive !== undefined) {
      searchParams.set('include_inactive', String(params.include_inactive));
    }
    const query = searchParams.toString();
    return request(`/api/admin/field-library${query ? `?${query}` : ''}`);
  },

  // 创建字段
  createField: async (data: {
    code: string;
    name: string;
    field_type?: string;
    category_id?: number | null;
    validation_rule?: string;
    default_value?: string;
    description?: string;
    options?: string;
  }): Promise<FieldLibraryItem> => {
    return request('/api/admin/field-library', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // 更新字段
  updateField: async (id: number, data: Partial<{
    name: string;
    field_type: string;
    category_id: number | null;
    validation_rule: string;
    default_value: string;
    description: string;
    options: string;
    is_active: boolean;
  }>): Promise<FieldLibraryItem> => {
    return request(`/api/admin/field-library/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // 删除字段
  deleteField: async (id: number): Promise<{ message: string }> => {
    return request(`/api/admin/field-library/${id}`, { method: 'DELETE' });
  },

  // 上传模板
  uploadTemplate: async (file: File, categoryId?: number, name?: string): Promise<TemplateUploadResult> => {
    const formData = new FormData();
    formData.append('file', file);
    if (categoryId) formData.append('category_id', String(categoryId));
    if (name) formData.append('name', name);

    const response = await fetch(`${API_BASE_URL}/api/admin/templates/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('staff_token')}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '上传失败');
    }

    return response.json();
  },

  // 获取模板预览
  getTemplatePreview: async (templateId: number): Promise<{
    template_id: number;
    template_name: string;
    category_id: number | null;
    content_text: string;
    content_html: string;
    status: string;
    mappings: Array<{
      id: number;
      source_type: string;
      source_text: string;
      position_index: number;
      field_id: number | null;
      field_name: string | null;
    }>;
  }> => {
    return request(`/api/admin/templates/${templateId}/preview`);
  },

  // 保存字段映射
  saveMappings: async (templateId: number, mappings: Array<{
    source_type: string;
    source_text: string;
    field_id: number | null;
  }>): Promise<{ message: string; mapping_count: number }> => {
    return request(`/api/admin/templates/${templateId}/save-mappings`, {
      method: 'POST',
      body: JSON.stringify(mappings),
    });
  },

  // 获取模板列表
  getTemplates: async (params?: {
    category_id?: number;
    status?: string;
  }): Promise<Array<{
    id: number;
    name: string;
    contract_type: string;
    category_id: number | null;
    status: string;
    created_at: string;
    updated_at: string;
  }>> => {
    const searchParams = new URLSearchParams();
    if (params?.category_id) searchParams.set('category_id', String(params.category_id));
    if (params?.status) searchParams.set('status', params.status);
    const query = searchParams.toString();
    return request(`/api/admin/templates${query ? `?${query}` : ''}`);
  },

  // 更新模板状态
  updateTemplateStatus: async (templateId: number, status: string): Promise<{ message: string }> => {
    return request(`/api/admin/templates/${templateId}/status?status=${status}`, {
      method: 'PUT',
    });
  },
};

// ==================== 合同审核 API ====================

export interface ContractReviewItem {
  id: number;
  contract_no: string;
  title: string | null;
  contract_type: string;
  status: string;
  user_id: number;
  user_name: string | null;
  assigned_reviewer_id: number | null;
  assigned_reviewer_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContractReviewListResponse {
  total: number;
  items: ContractReviewItem[];
}

export interface ContractReviewDetail {
  id: number;
  contract_no: string;
  title: string | null;
  contract_type: string;
  status: string;
  user_id: number;
  user_name: string | null;
  template_id: number | null;
  field_values: Record<string, unknown>;
  content: string | null;
  // 审核分配
  assigned_reviewer_id: number | null;
  assigned_reviewer_name: string | null;
  // 初审
  first_reviewed_by: number | null;
  first_reviewed_by_name: string | null;
  first_reviewed_at: string | null;
  first_review_comment: string | null;
  // 终审
  final_reviewed_by: number | null;
  final_reviewed_by_name: string | null;
  final_reviewed_at: string | null;
  final_review_comment: string | null;
  // 驳回
  rejected_by: number | null;
  rejected_by_name: string | null;
  rejected_at: string | null;
  reject_reason: string | null;
  // 合同编辑
  content_edited: string | null;
  content_edited_by: number | null;
  content_edited_by_name: string | null;
  content_edited_at: string | null;
  // 兼容旧字段
  reviewed_by: number | null;
  reviewed_by_name: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewActionResult {
  message: string;
  contract_id: number;
  status: string;
  signed_by: string;
  signed_at: string;
}

export interface ReviewLogItem {
  id: number;
  contract_id: number;
  action: string;
  operator_id: number;
  operator_name: string | null;
  operator_role: string | null;
  detail: Record<string, unknown> | null;
  created_at: string;
}

export interface ReviewLogResponse {
  total: number;
  items: ReviewLogItem[];
}

export const contractReviewApi = {
  // 获取合同列表
  getContracts: async (params?: {
    status?: string;
    contract_type?: string;
    user_id?: number;
    keyword?: string;
    start_date?: string;
    end_date?: string;
    skip?: number;
    limit?: number;
  }): Promise<ContractReviewListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    if (params?.contract_type) searchParams.set('contract_type', params.contract_type);
    if (params?.user_id) searchParams.set('user_id', String(params.user_id));
    if (params?.keyword) searchParams.set('keyword', params.keyword);
    if (params?.start_date) searchParams.set('start_date', params.start_date);
    if (params?.end_date) searchParams.set('end_date', params.end_date);
    if (params?.skip !== undefined) searchParams.set('skip', String(params.skip));
    if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
    const query = searchParams.toString();
    return request(`/api/admin/contracts${query ? `?${query}` : ''}`);
  },

  // 获取合同详情
  getContractDetail: async (contractId: number): Promise<ContractReviewDetail> => {
    return request(`/api/admin/contracts/${contractId}`);
  },

  // 获取合同类型列表
  getContractTypes: async (): Promise<Array<{ value: string; label: string }>> => {
    return request('/api/admin/contract-types');
  },

  // 获取合同状态列表
  getContractStatuses: async (): Promise<Array<{ value: string; label: string }>> => {
    return request('/api/admin/contract-statuses');
  },

  // 提交审核
  submitReview: async (contractId: number): Promise<ReviewActionResult> => {
    return request(`/api/admin/contracts/${contractId}/submit-review`, { method: 'POST' });
  },

  // 分配审核人
  assignReviewer: async (contractId: number, reviewerId: number): Promise<ReviewActionResult> => {
    return request(`/api/admin/contracts/${contractId}/assign`, {
      method: 'POST',
      body: JSON.stringify({ reviewer_id: reviewerId }),
    });
  },

  // 开始审核
  startReview: async (contractId: number): Promise<ReviewActionResult> => {
    return request(`/api/admin/contracts/${contractId}/start-review`, { method: 'POST' });
  },

  // 初审通过
  firstReviewPass: async (contractId: number, comment?: string): Promise<ReviewActionResult> => {
    return request(`/api/admin/contracts/${contractId}/first-review-pass`, {
      method: 'POST',
      body: JSON.stringify({ comment }),
    });
  },

  // 终审
  finalReview: async (
    contractId: number,
    action: 'pass' | 'reject',
    options?: { comment?: string; reject_reason?: string }
  ): Promise<ReviewActionResult> => {
    return request(`/api/admin/contracts/${contractId}/final-review`, {
      method: 'POST',
      body: JSON.stringify({ action, ...options }),
    });
  },

  // admin直接完成
  directComplete: async (contractId: number, comment?: string): Promise<ReviewActionResult> => {
    return request(`/api/admin/contracts/${contractId}/direct-complete`, {
      method: 'POST',
      body: JSON.stringify({ comment }),
    });
  },

  // 编辑合同内容
  editContent: async (contractId: number, content: string): Promise<ReviewActionResult> => {
    return request(`/api/admin/contracts/${contractId}/content`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    });
  },

  // 重新提交审核（驳回后）
  resubmitReview: async (contractId: number): Promise<ReviewActionResult> => {
    return request(`/api/admin/contracts/${contractId}/resubmit`, { method: 'POST' });
  },

  // 获取审核日志
  getReviewLogs: async (contractId: number): Promise<ReviewLogResponse> => {
    return request(`/api/admin/contracts/${contractId}/logs`);
  },

  // AI审核
  aiReview: async (contractId: number): Promise<{
    message: string;
    contract_id: number;
    status: string;
    report: {
      id: number;
      risk_summary: { high: number; medium: number; low: number };
      risk_items: Array<{
        id: string;
        level: string;
        type: string;
        title: string;
        content: string;
        reason: string;
        suggestion: string;
        status: string;
      }>;
      created_at: string;
    };
  }> => {
    return request(`/api/admin/contracts/${contractId}/ai-review`, { method: 'POST' });
  },

  // AI审核（SSE流式进度）
  aiReviewStream: (
    contractId: number,
    onProgress: (data: {
      step?: string;
      progress: number;
      status: string;
      message?: string;
      risk_items?: any[];
      found_count?: number;
      risk_summary?: { high: number; medium: number; low: number };
      new_status?: string;
      report?: any;
    }) => void,
    token: string
  ): Promise<{
    message: string;
    contract_id: number;
    status: string;
    report: any;
  }> => {
    return new Promise((resolve, reject) => {
      fetch(`${API_BASE_URL}/api/admin/contracts/${contractId}/ai-review`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'text/event-stream',
        },
      }).then(async response => {
        const reader = response.body?.getReader();
        if (!reader) {
          reject(new Error('无法读取响应流'));
          return;
        }

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                onProgress(data);

                if (data.status === 'saved') {
                  resolve({
                    message: 'AI审核完成',
                    contract_id: data.contract_id,
                    new_status: data.new_status,
                    status: data.new_status,
                    report: data.report
                  });
                }

                if (data.status === 'error') {
                  reject(new Error(data.message));
                }
              } catch (e) {
                // 忽略解析错误
              }
            }
          }
        }
      }).catch(reject);
    });
  },

  // 获取AI审核报告
  getReviewReport: async (contractId: number): Promise<{
    message: string;
    contract_id: number;
    report: {
      id: number;
      risk_summary: { high: number; medium: number; low: number };
      risk_items: Array<{
        id: string;
        level: string;
        type: string;
        title: string;
        reason: string;
        original_text?: string;
        suggested_text?: string;
        applied?: boolean;
      }>;
      ai_model: string;
      created_at: string;
    } | null;
  }> => {
    return request(`/api/admin/contracts/${contractId}/review-report`);
  },

  // 标记审核建议为已采纳
  applySuggestion: async (contractId: number, itemId: string): Promise<{
    message: string;
    item_id: string;
  }> => {
    return request(`/api/admin/contracts/${contractId}/apply-suggestion`, {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId }),
    });
  },

  // 格式化合同内容
  formatContract: async (contractId: number): Promise<{
    message: string;
    contract_id: number;
    original_content: string;
    formatted_content: string;
  }> => {
    return request(`/api/admin/contracts/${contractId}/format`, {
      method: 'POST',
    });
  },

  // 应用格式化后的内容
  applyFormat: async (contractId: number, content: string): Promise<{
    message: string;
    contract_id: number;
  }> => {
    return request(`/api/admin/contracts/${contractId}/apply-format`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  },
};
