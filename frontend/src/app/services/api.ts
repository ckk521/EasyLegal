/**
 * API 服务层 - 与后端交互
 */

const API_BASE_URL = 'http://localhost:8001';

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

  // 添加 token
  const token = localStorage.getItem('token');
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || '请求失败');
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
  // 获取LLM配置
  getLLMConfig: async (): Promise<LLMConfig> => {
    return request('/api/admin/config/llm');
  },

  // 创建LLM配置
  createLLMConfig: async (data: LLMConfigInput): Promise<LLMConfig> => {
    return request('/api/admin/config/llm', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // 更新LLM配置
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
