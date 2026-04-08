# 智能合同审核平台 - 技术架构设计

> 版本：V1.0
> 日期：2026-03-23

---

## 1. 系统架构

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端层 (React)                           │
├─────────────────────────────┬───────────────────────────────────┤
│        C端 (用户端)          │         B端 (管理后台)            │
│  ┌─────────────────────┐   │   ┌─────────────────────────────┐ │
│  │ 登录注册 │ 对话界面 │   │   │ 登录 │ 用户管理 │ 配置管理 │ │
│  │ 合同列表 │ 历史记录 │   │   │ 模板管理 │ 意图配置 │ 日志  │ │
│  └─────────────────────┘   │   └─────────────────────────────┘ │
└─────────────────────────────┴───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      后端层 (FastAPI)                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐│
│  │ 用户服务     │ │ Agent服务    │ │ 配置服务                 ││
│  │ - 注册登录   │ │ - 对话管理   │ │ - 大模型配置             ││
│  │ - 用户管理   │ │ - 意图识别   │ │ - Embedding配置          ││
│  │ - 权限控制   │ │ - RAG检索    │ │ - 意图/话术/敏感信息配置 ││
│  └──────────────┘ └──────────────┘ └──────────────────────────┘│
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐│
│  │ 合同服务     │ │ 文件服务     │ │ 审计服务                 ││
│  │ - 合同生成   │ │ - 模板上传   │ │ - 日志记录               ││
│  │ - 字段收集   │ │ - 文档解析   │ │ - 操作追踪               ││
│  │ - 文档导出   │ │ - RAG索引    │ │                          ││
│  └──────────────┘ └──────────────┘ └──────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据层                                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐│
│  │ SQLite       │ │ Chroma       │ │ 本地文件系统             ││
│  │ (结构化数据) │ │ (向量索引)   │ │ (模板/文档/合同)         ││
│  └──────────────┘ └──────────────┘ └──────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      外部服务                                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────┐│
│  │ 大模型API (B端可配置)                                       ││
│  │ - API KEY / BASE URL / MODEL NAME                          ││
│  └────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈

| 层级 | 技术选型 | 版本 |
|------|----------|------|
| 前端 | React + Ant Design | React 18, Ant Design 5.x |
| 后端 | Python + FastAPI | Python 3.10+, FastAPI 0.100+ |
| AI框架 | LangChain | 0.1.x |
| 向量库 | Chroma | 0.4.x |
| Embedding | m3e-base | 本地部署 |
| 数据库 | SQLite | 3.x |
| 部署 | Docker + Docker Compose | 最新版 |

---

## 2. 模块设计

### 2.1 后端模块划分

```
backend/
├── app/
│   ├── main.py                 # 应用入口
│   ├── config.py               # 配置管理
│   ├── database.py             # 数据库连接
│   │
│   ├── models/                 # 数据模型
│   │   ├── user.py
│   │   ├── chat.py
│   │   ├── contract.py
│   │   ├── config.py
│   │   └── audit.py
│   │
│   ├── schemas/                # Pydantic模型
│   │   ├── user.py
│   │   ├── chat.py
│   │   ├── contract.py
│   │   └── config.py
│   │
│   ├── routers/                # API路由
│   │   ├── auth.py             # 认证相关
│   │   ├── user.py             # 用户管理
│   │   ├── chat.py             # 对话相关
│   │   ├── contract.py         # 合同相关
│   │   ├── config.py           # 配置管理
│   │   ├── file.py             # 文件上传
│   │   └── admin.py            # B端管理
│   │
│   ├── services/               # 业务逻辑
│   │   ├── user_service.py
│   │   ├── chat_service.py
│   │   ├── contract_service.py
│   │   ├── config_service.py
│   │   ├── file_service.py
│   │   └── audit_service.py
│   │
│   ├── agent/                  # Agent模块
│   │   ├── __init__.py
│   │   ├── agent.py            # LangChain Agent主类
│   │   ├── intent.py           # 意图识别
│   │   ├── rag.py              # RAG检索
│   │   ├── tools/              # Agent工具
│   │   │   ├── contract_tool.py
│   │   │   ├── knowledge_tool.py
│   │   │   └── reject_tool.py
│   │   └── prompts/            # 提示词模板
│   │       ├── system_prompt.py
│   │       └── intent_prompt.py
│   │
│   ├── utils/                  # 工具函数
│   │   ├── auth.py             # JWT认证
│   │   ├── sensitive.py        # 敏感信息处理
│   │   ├── document.py         # 文档处理
│   │   └── export.py           # 合同导出
│   │
│   └── static/                 # 前端静态文件
│
├── data/                       # 数据目录
│   ├── templates/
│   ├── documents/
│   ├── rag_index/
│   ├── contracts/
│   └── logs/
│
├── tests/                      # 测试
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### 2.2 前端模块划分

```
frontend/
├── public/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   │
│   ├── pages/                  # 页面
│   │   ├── c/                  # C端页面
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── Chat.tsx
│   │   │   ├── ContractList.tsx
│   │   │   ├── ContractDetail.tsx
│   │   │   └── History.tsx
│   │   │
│   │   └── b/                  # B端页面
│   │       ├── Login.tsx
│   │       ├── Dashboard.tsx
│   │       ├── UserManage.tsx
│   │       ├── ConfigLLM.tsx
│   │       ├── ConfigEmbedding.tsx
│   │       ├── TemplateManage.tsx
│   │       ├── IntentConfig.tsx
│   │       ├── LegalScopeConfig.tsx
│   │       ├── RejectScriptConfig.tsx
│   │       ├── SensitiveConfig.tsx
│   │       ├── DocumentManage.tsx
│   │       ├── ChatHistory.tsx
│   │       └── ContractHistory.tsx
│   │
│   ├── components/             # 通用组件
│   │   ├── ChatBox.tsx
│   │   ├── ContractForm.tsx
│   │   ├── FileUpload.tsx
│   │   └── JsonEditor.tsx
│   │
│   ├── services/               # API服务
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   ├── chat.ts
│   │   ├── contract.ts
│   │   └── config.ts
│   │
│   ├── stores/                 # 状态管理
│   │   └── userStore.ts
│   │
│   └── utils/                  # 工具函数
│       ├── request.ts
│       └── storage.ts
│
├── package.json
└── vite.config.ts
```

---

## 3. API设计

### 3.1 认证相关 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/auth/register` | C端用户注册 | 公开 |
| POST | `/api/auth/login` | 用户登录 | 公开 |
| POST | `/api/auth/logout` | 退出登录 | 登录用户 |
| GET | `/api/auth/me` | 获取当前用户信息 | 登录用户 |

### 3.2 用户管理 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/admin/users` | 获取用户列表 | admin |
| PUT | `/api/admin/users/{id}/status` | 启用/禁用用户 | admin |
| DELETE | `/api/admin/users/{id}` | 删除用户 | admin |

### 3.3 对话相关 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/chat/sessions` | 获取会话列表 | C端用户 |
| POST | `/api/chat/sessions` | 创建新会话 | C端用户 |
| GET | `/api/chat/sessions/{id}` | 获取会话详情 | C端用户 |
| DELETE | `/api/chat/sessions/{id}` | 删除会话 | C端用户 |
| GET | `/api/chat/sessions/{id}/messages` | 获取会话消息 | C端用户 |
| PUT | `/api/chat/messages/{id}` | 编辑消息 | C端用户 |
| DELETE | `/api/chat/messages/{id}` | 删除消息 | C端用户 |
| **GET** | `/api/chat/stream` | **SSE对话流** | C端用户 |

### 3.4 SSE对话接口详细设计

**请求**：`GET /api/chat/stream`

**参数**（Query String）：
```
session_id: string    # 会话ID
message: string      # 用户消息
```

**响应**：SSE流

```
event: message
data: {"type": "token", "content": "您"}

event: message
data: {"type": "token", "content": "好"}

event: message
data: {"type": "intent", "intent": "contract_generate"}

event: message
data: {"type": "action", "action": "collect_field", "field": "出租方"}

event: message
data: {"type": "done", "message_id": "msg_xxx"}
```

### 3.5 合同相关 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/contracts` | 获取合同列表 | C端用户 |
| POST | `/api/contracts` | 创建合同 | C端用户 |
| GET | `/api/contracts/{id}` | 获取合同详情 | C端用户 |
| PUT | `/api/contracts/{id}` | 更新合同 | C端用户 |
| DELETE | `/api/contracts/{id}` | 删除合同 | C端用户 |
| POST | `/api/contracts/{id}/generate` | 生成合同文档 | C端用户 |
| GET | `/api/contracts/{id}/export` | 导出合同(PDF) | C端用户 |

### 3.6 配置管理 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/config/llm` | 获取大模型配置 | admin |
| PUT | `/api/config/llm` | 更新大模型配置 | admin |
| GET | `/api/config/embedding` | 获取Embedding配置 | admin |
| PUT | `/api/config/embedding` | 更新Embedding配置 | admin |
| GET | `/api/config/intent` | 获取意图配置列表 | admin |
| POST | `/api/config/intent` | 上传意图配置 | admin |
| PUT | `/api/config/intent/{id}` | 更新意图配置 | admin |
| DELETE | `/api/config/intent/{id}` | 删除意图配置 | admin |
| GET | `/api/config/legal-scope` | 获取法律范围配置 | admin |
| PUT | `/api/config/legal-scope` | 更新法律范围配置 | admin |
| GET | `/api/config/reject-script` | 获取拒绝话术配置 | admin |
| PUT | `/api/config/reject-script` | 更新拒绝话术配置 | admin |
| GET | `/api/config/sensitive` | 获取敏感信息配置 | admin |
| PUT | `/api/config/sensitive` | 更新敏感信息配置 | admin |

### 3.7 文件管理 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/files/template` | 上传合同模板 | admin |
| GET | `/api/files/templates` | 获取模板列表 | admin |
| DELETE | `/api/files/templates/{id}` | 删除模板 | admin |
| POST | `/api/files/document` | 上传文档(案例/审核规则) | admin |
| GET | `/api/files/documents` | 获取文档列表 | admin |
| DELETE | `/api/files/documents/{id}` | 删除文档 | admin |

### 3.8 B端管理 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/admin/chat-history` | 获取C端聊天记录 | admin |
| GET | `/api/admin/contracts` | 获取C端合同列表 | admin |
| GET | `/api/admin/audit-logs` | 获取审计日志 | admin |

---

## 4. 核心流程设计

### 4.1 对话流程

```
┌──────────────────────────────────────────────────────────────────┐
│                        用户发送消息                               │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      1. 意图识别                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 混合策略：关键词 + 正则 + 语义相似度 + LLM辅助                 │ │
│  │ 输入：用户消息 + 核心意图配置(B端)                            │ │
│  │ 输出：意图类型 + 置信度                                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    2. 法律范围判断                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 非法律问题 → 使用拒绝话术(B端配置) → 返回拒绝响应             │ │
│  │ 法律问题 → 继续处理                                         │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      3. 意图分流                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 合同生成 → 调用合同生成流程                                  │ │
│  │ 知识查询 → RAG检索 → 返回答案                               │ │
│  │ 合同状态查询 → 查询数据库 → 返回状态                        │ │
│  │ 转人工 → 返回转人工提示                                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      4. 响应生成                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 调用大模型API → 流式生成响应 → SSE推送给前端                 │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 合同生成流程

```
┌──────────────────────────────────────────────────────────────────┐
│                   用户表达合同需求                                │
│                   "我要租房子，帮我写一份合同"                     │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                   1. 创建合同会话                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ - 创建chat_session记录                                      │ │
│  │ - 创建contract记录(状态: 草稿)                              │ │
│  │ - 关联session和contract                                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                   2. 字段收集(逐个提问)                           │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 循环：                                                       │ │
│  │   - 获取下一个未填写的必填字段                               │ │
│  │   - Agent生成提问                                            │ │
│  │   - 用户回答                                                 │ │
│  │   - 提取并验证字段值                                         │ │
│  │   - 保存到contract_data                                      │ │
│  │ 直到所有必填字段收集完成                                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                   3. 合同生成                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ - 加载合同模板                                               │ │
│  │ - 填充字段值                                                 │ │
│  │ - AI润色(可选)                                               │ │
│  │ - 生成合同内容                                               │ │
│  │ - 更新合同状态为"待确认"                                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                   4. 用户确认                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ - 展示合同预览                                               │ │
│  │ - 用户可修改或确认                                           │ │
│  │ - 确认后状态变为"已完成"                                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                   5. 导出PDF                                      │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ - 生成PDF文件                                                │ │
│  │ - 保存到/data/contracts/                                     │ │
│  │ - 返回下载链接                                               │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. Agent设计

### 5.1 智能体决策循环架构（核心）

> 更新日期：2026-04-08
> 设计理念：让 LLM 做决策和思考，结合深度反思机制，实现真正的智能体行为

#### 5.1.1 架构演进

**旧架构问题**：硬编码流水线

```
意图分类(5类) → if-else选工具 → 执行 → 浅层反思(只检查成功/失败)
```

问题：
- 意图分类是离散标签，无法表达连续语义
- 工具选择是硬编码逻辑，无法灵活处理
- 关键信息（合同类型）在意图分类阶段丢失
- 反思太浅，没有回溯到用户意图

**新架构**：LLM 决策 + 深度反思循环

```
┌─────────────────────────────────────────────────────────────────────┐
│                           用户输入                                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     [LLM 思考决策]                                   │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ 输入：用户消息 + 对话历史 + 可用工具列表                         │ │
│  │ 输出：{                                                         │ │
│  │   thinking: "理解用户意图的思考过程",                           │ │
│  │   action: "工具名称或done",                                     │ │
│  │   args: {参数},                                                 │ │
│  │   expected_result: "期望的结果"                                 │ │
│  │ }                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        [执行工具]                                    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     [深度反思评估]                                   │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ 输入：用户意图 + 决策理由 + 期望结果 + 实际结果                  │ │
│  │                                                                 │ │
│  │ 反思问题：                                                       │ │
│  │ 1. 结果是否真正满足用户需求？                                    │ │
│  │ 2. 我对用户意图的理解是否正确？                                  │ │
│  │ 3. 工具选择是否恰当？                                            │ │
│  │ 4. 是否需要追问用户澄清？                                        │ │
│  │                                                                 │ │
│  │ 输出：{                                                         │ │
│  │   satisfied: true/false,                                        │ │
│  │   score: 0.0-1.0,                                               │ │
│  │   reason: "不满意的原因",                                        │ │
│  │   correct_action: "纠正后的工具",                               │ │
│  │   user_question: "需要追问的问题"                                │ │
│  │ }                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
              satisfied=false                satisfied=true
                    │                               │
                    ▼                               ▼
        ┌─────────────────────┐         ┌─────────────────────┐
        │   [纠正重试]         │         │   [输出响应]         │
        │                     │         │                     │
        │ 根据 reason 决定：   │         │ 返回最终结果给用户   │
        │ - 重试同一工具       │         └─────────────────────┘
        │ - 换其他工具         │
        │ - 追问用户澄清       │
        └─────────────────────┘
                    │
                    └──────────→ 循环（最多5次）
```

#### 5.1.2 关键设计点

**1. LLM 决策输出结构**

```json
{
  "thinking": "用户问有没有买卖交易模板，他想知道我们是否有这类模板，应该搜索买卖相关的模板",
  "action": "get_template_list",
  "args": {"contract_type": "买卖交易"},
  "expected_result": "返回买卖相关的模板列表"
}
```

**2. 深度反思机制**

```json
{
  "thinking": "工具返回了类型选择，但用户已经说了'买卖交易'，我应该直接搜索买卖模板",
  "satisfied": false,
  "score": 0.3,
  "reason": "理解错了用户意图，用户不是要选类型，是要看模板列表",
  "correct_action": "get_template_list",
  "correct_args": {"contract_type": "买卖交易"}
}
```

**3. 迭代保护**

- 最大迭代次数：5
- 每次迭代记录决策和反思过程
- 超过限制时返回当前最佳结果

#### 5.1.3 示例场景

| 用户输入 | 错误流程（旧架构） | 正确流程（新架构） |
|---------|-------------------|-------------------|
| 有买卖交易模板吗？ | 意图=ask_type → 让用户选类型 | 决策=搜索买卖模板 → 直接返回列表 |
| 你们支持什么合同？ | 意图=unknown → 打招呼 | 决策=展示类型列表 → 返回所有类型 |
| 买卖合同怎么写？ | 意图=consult → RAG搜索 | 决策=获取买卖表单 → 返回填写界面 |
| 有没有劳动方面的？ | 意图=ask_type → 让用户选类型 | 决策=搜索劳动模板 → 直接返回列表 |

#### 5.1.4 反思触发条件

| 条件 | 触发反思 |
|------|---------|
| 工具返回成功 | ✅ 评估结果是否满足用户意图 |
| 工具返回失败 | ✅ 分析失败原因，决定重试或换工具 |
| 返回类型选择但用户已提到类型 | ✅ 纠正：直接搜索该类型 |
| 返回空结果 | ✅ 分析是否需要追问用户 |
| 用户意图模糊 | ✅ 追问澄清 |

### 5.2 Agent代码实现

```python
# agent/contract_agent.py

from typing import List, Dict, Any, Optional
from pydantic.v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

class Decision(BaseModel):
    """LLM决策输出"""
    thinking: str = Field(description="思考过程")
    action: str = Field(description="工具名称或done")
    args: Dict = Field(default={}, description="工具参数")
    expected_result: str = Field(description="期望的结果")

class Reflection(BaseModel):
    """反思输出"""
    thinking: str = Field(description="反思过程")
    satisfied: bool = Field(description="是否满意")
    score: float = Field(description="满意度0-1")
    reason: str = Field(description="不满意原因")
    correct_action: Optional[str] = Field(default=None, description="纠正后的工具")
    correct_args: Optional[Dict] = Field(default=None, description="纠正后的参数")
    user_question: Optional[str] = Field(default=None, description="追问用户的问题")

class ContractAgent:
    """智能体 - LLM决策 + 深度反思循环"""

    MAX_ITERATIONS = 5

    async def run(self, user_input: str) -> Dict:
        iteration = 0
        decision = None
        result = None

        while iteration < self.MAX_ITERATIONS:
            iteration += 1

            # 1. LLM决策
            decision = await self._make_decision(user_input, result)

            if decision.action == "done":
                return self._format_response(result)

            # 2. 执行工具
            result = await self._execute_tool(decision.action, decision.args)

            # 3. 深度反思
            reflection = await self._reflect(user_input, decision, result)

            if reflection.satisfied:
                return self._format_response(result)

            # 4. 纠正
            if reflection.correct_action:
                decision.action = reflection.correct_action
                decision.args = reflection.correct_args or {}
            elif reflection.user_question:
                return {"content": reflection.user_question, "need_clarify": True}

        return self._format_response(result)

    async def _make_decision(self, user_input: str, last_result: Dict) -> Decision:
        """LLM思考决策"""
        prompt = f"""
分析用户意图，决定下一步操作。

用户输入：{user_input}
上一步结果：{last_result or "无"}

可用工具：
- get_template_list: 搜索模板，参数 contract_type
- get_contract_form: 获取表单，参数 contract_type, template_id
- ask_contract_type: 展示所有类型选择
- rag_search: 法律咨询，参数 query

请输出JSON：
{{"thinking": "思考过程", "action": "工具名", "args": {{}}, "expected_result": "期望结果"}}
"""
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return self._parse_decision(response.content)

    async def _reflect(self, user_input: str, decision: Decision, result: Dict) -> Reflection:
        """深度反思评估"""
        prompt = f"""
评估工具执行结果是否真正满足用户需求。

用户意图：{user_input}
我的决策：{decision.action}({decision.args})
决策理由：{decision.thinking}
期望结果：{decision.expected_result}
实际结果：{result}

请回答：
1. 结果是否满足了用户的真实需求？
2. 我对用户意图的理解是否正确？
3. 如果不满意，应该怎么做？

输出JSON：
{{"thinking": "反思过程", "satisfied": true/false, "score": 0.0-1.0, "reason": "原因", "correct_action": "纠正工具", "correct_args": {{}}}}
"""
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return self._parse_reflection(response.content)
```

### 5.3 工具定义

```python
# agent/agent.py

from langchain.agents import AgentExecutor
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory

class ContractAgent:
    def __init__(self, config: dict):
        self.llm = self._init_llm(config)
        self.memory = ConversationBufferMemory()
        self.tools = self._init_tools()
        self.intent_classifier = IntentClassifier()
        self.rag_engine = RAGEngine()

    def _init_llm(self, config):
        """根据B端配置初始化大模型"""
        return ChatOpenAI(
            api_key=config['api_key'],
            base_url=config['base_url'],
            model=config['model_name'],
            streaming=True
        )

    def _init_tools(self):
        """初始化Agent工具"""
        return [
            ContractGenerateTool(),
            KnowledgeQueryTool(),
            ContractStatusTool(),
            RejectTool()
        ]

    async def chat(self, message: str, session_id: str):
        """处理用户消息"""
        # 1. 意图识别
        intent = await self.intent_classifier.classify(message)

        # 2. 法律范围判断
        if not self._is_legal_question(message):
            yield self._get_reject_response()
            return

        # 3. 根据意图执行对应工具
        if intent.type == "contract_generate":
            async for chunk in self._handle_contract_generate(message, session_id):
                yield chunk
        elif intent.type == "knowledge_query":
            async for chunk in self._handle_knowledge_query(message):
                yield chunk
        elif intent.type == "contract_status":
            async for chunk in self._handle_contract_status(session_id):
                yield chunk
        else:
            yield self._get_default_response()
```

### 5.2 意图识别设计

```python
# agent/intent.py

class IntentClassifier:
    def __init__(self):
        self.keyword_matcher = KeywordMatcher()
        self.regex_matcher = RegexMatcher()
        self.semantic_matcher = SemanticMatcher()
        self.llm_assistant = LLMAssistant()

    async def classify(self, message: str) -> Intent:
        """混合策略意图识别"""

        # 1. 关键词匹配
        intent = self.keyword_matcher.match(message)
        if intent and intent.confidence > 0.9:
            return intent

        # 2. 正则匹配
        intent = self.regex_matcher.match(message)
        if intent and intent.confidence > 0.8:
            return intent

        # 3. 语义相似度
        intent = await self.semantic_matcher.match(message)
        if intent and intent.confidence > 0.7:
            return intent

        # 4. LLM辅助判断
        intent = await self.llm_assistant.classify(message)
        return intent
```

### 5.3 RAG检索设计

```python
# agent/rag.py

from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings

class RAGEngine:
    def __init__(self, config: dict):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="m3e-base"
        )
        self.vectorstore = Chroma(
            persist_directory="./data/rag_index",
            embedding_function=self.embeddings
        )
        self.chunk_size = config.get('chunk_size', 512)
        self.overlap = config.get('overlap', 50)

    async def query(self, question: str, top_k: int = 5) -> list:
        """检索相关文档"""
        results = self.vectorstore.similarity_search(
            question,
            k=top_k
        )
        return results

    def add_documents(self, documents: list):
        """添加文档到向量库"""
        self.vectorstore.add_documents(documents)
        self.vectorstore.persist()
```

---

## 6. 安全设计

### 6.1 认证机制

```python
# utils/auth.py

from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = "your-secret-key"  # 生产环境从环境变量读取
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
```

### 6.2 敏感信息处理

```python
# utils/sensitive.py

import re

class SensitiveHandler:
    def __init__(self, rules: list):
        self.rules = rules

    def mask(self, text: str) -> str:
        """对文本中的敏感信息进行掩码"""
        for rule in self.rules:
            if rule['type'] == 'id_card':
                text = self._mask_id_card(text, rule)
            elif rule['type'] == 'bank_card':
                text = self._mask_bank_card(text, rule)
            elif rule['type'] == 'address':
                text = self._mask_address(text, rule)
        return text

    def _mask_id_card(self, text: str, rule: dict) -> str:
        pattern = r'\d{17}[\dXx]'
        return re.sub(pattern, lambda m: m.group()[:3] + '*'*11 + m.group()[-4:], text)

    def _mask_bank_card(self, text: str, rule: dict) -> str:
        pattern = r'\d{16,19}'
        return re.sub(pattern, lambda m: m.group()[:4] + '*'*(len(m.group())-8) + m.group()[-4:], text)
```

---

## 7. 部署架构

### 7.1 Docker部署

```yaml
# docker-compose.yml

version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - SECRET_KEY=${SECRET_KEY}
    restart: unless-stopped
```

```dockerfile
# Dockerfile

FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://registry.npmmirror.com/simple

# 复制代码
COPY . .

# 构建前端
RUN pip install nodeenv && nodeenv -p && npm install && npm run build

# 启动服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 8. 性能优化

### 8.1 SQLite优化

```python
# database.py

import sqlite3

# 启用WAL模式，提高并发性能
conn = sqlite3.connect('data/app.db')
conn.execute('PRAGMA journal_mode=WAL')
conn.execute('PRAGMA synchronous=NORMAL')
conn.execute('PRAGMA cache_size=10000')
conn.execute('PRAGMA temp_store=MEMORY')
```

### 8.2 缓存策略

| 数据类型 | 缓存策略 |
|----------|----------|
| B端配置 | 内存缓存，配置变更时失效 |
| RAG索引 | Chroma自带缓存 |
| 用户会话 | 不缓存 |
| 合同模板 | 内存缓存 |

---

## 9. 监控与日志

### 9.1 日志配置

```python
# 日志格式
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# 审计日志单独文件
audit_logger = logging.getLogger('audit')
audit_handler = logging.FileHandler('data/logs/audit.log')
audit_logger.addHandler(audit_handler)
```

### 9.2 健康检查

| 接口 | 说明 |
|------|------|
| GET `/health` | 服务健康检查 |
| GET `/metrics` | Prometheus指标（可选） |
