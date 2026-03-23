# 智能合同审核平台 - 系统架构设计

> 版本：V1.0
> 日期：2026-03-23
> 状态：设计阶段

---

## 1. 系统概述

### 1.1 设计目标

- **配置驱动**：C端智能体的所有行为依赖B端配置，运营人员无需修改代码即可调整Agent策略
- **MVP优先**：快速交付核心功能，支持迭代扩展
- **轻量部署**：单机Docker部署，SQLite存储，降低运维成本

### 1.2 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | React 18 + Ant Design 5 | 企业级UI组件库 |
| 后端 | Python 3.11 + FastAPI | 异步高性能，AI生态友好 |
| 数据库 | SQLite | 轻量级本地存储，MVP阶段够用 |
| 向量库 | Chroma | 本地向量数据库，无需额外服务 |
| AI框架 | LangChain | 成熟的LLM应用框架 |
| Embedding | m3e-base | 国产中文模型，本地部署 |
| 部署 | Docker + Docker Compose | 容器化部署，易于管理 |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                           客户端层                                   │
├─────────────────────────────────────┬───────────────────────────────┤
│         C端 Web (React)             │      B端 Web (React)          │
│    ┌─────────────────────────┐     │    ┌─────────────────────┐    │
│    │  登录/注册  对话界面    │     │    │  登录  后台管理     │    │
│    │  历史聊天  合同管理     │     │    │  配置  模板管理     │    │
│    └─────────────────────────┘     │    └─────────────────────┘    │
└─────────────────────────────────────┴───────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         API网关层 (FastAPI)                          │
├─────────────────────────────────────────────────────────────────────┤
│  /api/auth/*        认证授权接口                                     │
│  /api/chat/*        对话相关接口 (SSE流式)                           │
│  /api/contract/*    合同相关接口                                     │
│  /api/admin/*       B端管理接口                                      │
│  /api/config/*      配置管理接口                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          业务服务层                                  │
├──────────────┬──────────────┬──────────────┬────────────────────────┤
│  用户服务    │   对话服务   │   合同服务   │      配置服务          │
│  UserService │  ChatService │ContractService│   ConfigService        │
├──────────────┴──────────────┴──────────────┴────────────────────────┤
│                          Agent服务层                                 │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    LangChain Agent                           │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │   │
│  │  │意图识别   │  │ RAG检索  │  │合同生成   │  │对话管理  │   │   │
│  │  │IntentEngine│ │ RAGEngine│ │ContractGen│ │DialogMgr │   │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          数据存储层                                  │
├──────────────┬──────────────┬──────────────┬────────────────────────┤
│   SQLite     │   Chroma     │  文件系统     │    审计日志           │
│  (业务数据)  │  (向量索引)  │  (模板/文档)  │    (操作记录)         │
└──────────────┴──────────────┴──────────────┴────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          外部服务层                                  │
├─────────────────────────────────────────────────────────────────────┤
│              大模型API (OpenAI兼容接口)                              │
│         API KEY / BASE URL / MODEL NAME (B端配置)                   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 模块职责

#### 2.2.1 API网关层

| 模块 | 职责 | 主要接口 |
|------|------|----------|
| AuthRouter | 用户认证授权 | POST /login, POST /register, POST /logout |
| ChatRouter | 对话管理 | POST /chat/send, GET /chat/history, GET /chat/stream |
| ContractRouter | 合同管理 | CRUD /contract/* |
| AdminRouter | B端后台管理 | CRUD /admin/users, /admin/templates, /admin/config |
| ConfigRouter | 配置管理 | GET/PUT /config/llm, /config/embedding, /config/intent |

#### 2.2.2 业务服务层

| 服务 | 职责 | 依赖 |
|------|------|------|
| UserService | 用户注册、登录、权限管理 | SQLite |
| ChatService | 对话历史管理、会话管理 | SQLite, AgentService |
| ContractService | 合同CRUD、字段收集、文档生成 | SQLite, TemplateService |
| ConfigService | 配置项管理、实时生效 | SQLite |

#### 2.2.3 Agent服务层

| 组件 | 职责 | 输入 | 输出 |
|------|------|------|------|
| IntentEngine | 意图识别（混合策略） | 用户消息 | 意图类型 + 置信度 |
| RAGEngine | RAG检索增强 | Query | 相关文档片段 |
| ContractGen | 合同生成 | 字段数据 | 合同文档 |
| DialogManager | 对话状态管理 | 消息上下文 | 下一步动作 |

---

## 3. 核心流程设计

### 3.1 对话流程

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 用户    │───▶│ API网关 │───▶│意图识别 │───▶│意图分流 │───▶│响应生成 │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                   │              │              │              │
                   │              │              │              │
                   ▼              ▼              ▼              ▼
               ┌─────────────────────────────────────────────────────┐
               │                    意图类型                         │
               ├─────────────────────────────────────────────────────┤
               │  合同生成 ──▶ 字段收集 ──▶ 模板填充 ──▶ 文档导出    │
               │  知识查询 ──▶ RAG检索 ──▶ 答案生成                  │
               │  合同状态 ──▶ 数据库查询 ──▶ 状态展示               │
               │  非法律问题 ──▶ 拒绝话术 ──▶ 引导回归               │
               └─────────────────────────────────────────────────────┘
```

### 3.2 意图识别流程

```
用户消息
    │
    ▼
┌─────────────────┐
│  关键词匹配     │──▶ 命中 ──▶ 返回意图
└─────────────────┘
    │ 未命中
    ▼
┌─────────────────┐
│  正则表达式匹配 │──▶ 命中 ──▶ 返回意图
└─────────────────┘
    │ 未命中
    ▼
┌─────────────────┐
│  语义相似度计算 │──▶ 阈值以上 ──▶ 返回意图
│  (Embedding)    │
└─────────────────┘
    │ 阈值以下
    ▼
┌─────────────────┐
│  LLM辅助判断    │──▶ 返回意图 + 置信度
└─────────────────┘
```

### 3.3 合同生成流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                        合同生成状态机                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌────────┐    识别意图    ┌────────┐    字段收集    ┌────────┐   │
│   │  空闲  │──────────────▶│ 初始化 │──────────────▶│ 收集中 │   │
│   └────────┘               └────────┘               └────────┘   │
│       ▲                                                   │       │
│       │                                                   │       │
│       │              ┌────────┐    确认    ┌────────┐   │       │
│       │              │ 已完成 │◀──────────│ 待确认 │◀──┘       │
│       │              └────────┘           └────────┘           │
│       │                  │                    ▲                │
│       │                  │ 导出               │ 生成           │
│       │                  ▼                    │                │
│       │              ┌────────┐        ┌────────┐              │
│       └──────────────│ 已导出 │◀───────│ 生成中 │              │
│                      └────────┘        └────────┘              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. 目录结构设计

```
easyagent/
├── backend/                      # 后端服务
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI入口
│   │   ├── config.py            # 配置管理
│   │   ├── database.py          # 数据库连接
│   │   │
│   │   ├── api/                 # API路由
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          # 认证接口
│   │   │   ├── chat.py          # 对话接口
│   │   │   ├── contract.py      # 合同接口
│   │   │   ├── admin.py         # B端管理接口
│   │   │   └── config.py        # 配置接口
│   │   │
│   │   ├── services/            # 业务服务
│   │   │   ├── __init__.py
│   │   │   ├── user_service.py
│   │   │   ├── chat_service.py
│   │   │   ├── contract_service.py
│   │   │   └── config_service.py
│   │   │
│   │   ├── agent/               # Agent模块
│   │   │   ├── __init__.py
│   │   │   ├── intent_engine.py # 意图识别
│   │   │   ├── rag_engine.py    # RAG检索
│   │   │   ├── contract_gen.py  # 合同生成
│   │   │   ├── dialog_manager.py# 对话管理
│   │   │   └── llm_client.py    # LLM客户端
│   │   │
│   │   ├── models/              # 数据模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── chat.py
│   │   │   ├── contract.py
│   │   │   ├── config.py
│   │   │   └── document.py
│   │   │
│   │   ├── schemas/             # Pydantic模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── chat.py
│   │   │   ├── contract.py
│   │   │   └── config.py
│   │   │
│   │   └── utils/               # 工具函数
│   │       ├── __init__.py
│   │       ├── security.py      # 安全工具
│   │       ├── audit.py         # 审计日志
│   │       └── mask.py          # 敏感信息掩码
│   │
│   ├── data/                    # 数据目录
│   │   ├── templates/           # 合同模板
│   │   ├── documents/           # 案例、审核规则等
│   │   ├── rag_index/           # Chroma向量索引
│   │   ├── contracts/           # 生成的合同文档
│   │   └── logs/                # 审计日志
│   │
│   ├── tests/                   # 测试
│   │   ├── __init__.py
│   │   ├── test_auth.py
│   │   ├── test_chat.py
│   │   └── test_contract.py
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                     # 前端服务
│   ├── src/
│   │   ├── components/          # 公共组件
│   │   │   ├── ChatBox/         # 对话组件
│   │   │   ├── ContractForm/    # 合同表单
│   │   │   └── ConfigEditor/    # 配置编辑器
│   │   │
│   │   ├── pages/               # 页面
│   │   │   ├── c端/
│   │   │   │   ├── Login.tsx
│   │   │   │   ├── Register.tsx
│   │   │   │   ├── Chat.tsx
│   │   │   │   ├── History.tsx
│   │   │   │   └── Contracts.tsx
│   │   │   └── b端/
│   │   │       ├── Login.tsx
│   │   │       ├── Dashboard.tsx
│   │   │       ├── UserManage.tsx
│   │   │       ├── TemplateManage.tsx
│   │   │       └── ConfigManage.tsx
│   │   │
│   │   ├── services/            # API服务
│   │   │   ├── auth.ts
│   │   │   ├── chat.ts
│   │   │   ├── contract.ts
│   │   │   └── config.ts
│   │   │
│   │   ├── stores/              # 状态管理
│   │   │   ├── userStore.ts
│   │   │   └── chatStore.ts
│   │   │
│   │   ├── utils/               # 工具函数
│   │   │   ├── request.ts       # HTTP请求封装
│   │   │   └── sse.ts           # SSE客户端
│   │   │
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## 5. 接口设计

### 5.1 认证接口

| 方法 | 路径 | 说明 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| POST | /api/auth/register | 用户注册 | `{phone, email, password}` | `{user_id}` |
| POST | /api/auth/login | 用户登录 | `{account, password}` | `{token, user}` |
| POST | /api/auth/logout | 用户登出 | - | `{success}` |

### 5.2 对话接口

| 方法 | 路径 | 说明 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| POST | /api/chat/send | 发送消息 | `{session_id, content}` | SSE流 |
| GET | /api/chat/stream | SSE连接 | `?session_id=xxx` | SSE流 |
| GET | /api/chat/history | 历史消息 | `?session_id=xxx` | `[{messages}]` |
| GET | /api/chat/sessions | 会话列表 | - | `[{sessions}]` |
| DELETE | /api/chat/session/{id} | 删除会话 | - | `{success}` |

### 5.3 合同接口

| 方法 | 路径 | 说明 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| GET | /api/contract/list | 合同列表 | `?status=xxx` | `[{contracts}]` |
| GET | /api/contract/{id} | 合同详情 | - | `{contract}` |
| PUT | /api/contract/{id}/fields | 更新字段 | `{fields}` | `{contract}` |
| POST | /api/contract/{id}/generate | 生成合同 | - | `{contract_id}` |
| GET | /api/contract/{id}/export | 导出合同 | `?format=pdf` | 文件流 |
| DELETE | /api/contract/{id} | 删除合同 | - | `{success}` |

### 5.4 B端管理接口

| 方法 | 路径 | 说明 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| GET | /api/admin/users | 用户列表 | `?role=xxx` | `[{users}]` |
| PUT | /api/admin/users/{id}/status | 启用/禁用 | `{status}` | `{success}` |
| DELETE | /api/admin/users/{id} | 删除用户 | - | `{success}` |
| POST | /api/admin/templates | 上传模板 | multipart | `{template_id}` |
| GET | /api/admin/templates | 模板列表 | - | `[{templates}]` |
| DELETE | /api/admin/templates/{id} | 删除模板 | - | `{success}` |
| POST | /api/admin/documents | 上传文档 | multipart | `{doc_id}` |
| GET | /api/admin/documents | 文档列表 | `?type=xxx` | `[{docs}]` |

### 5.5 配置接口

| 方法 | 路径 | 说明 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| GET | /api/config/llm | 获取LLM配置 | - | `{config}` |
| PUT | /api/config/llm | 更新LLM配置 | `{api_key, base_url, model}` | `{success}` |
| GET | /api/config/embedding | 获取Embedding配置 | - | `{config}` |
| PUT | /api/config/embedding | 更新Embedding配置 | `{model, chunk_size, overlap}` | `{success}` |
| GET | /api/config/intent | 获取意图配置 | - | `[{intents}]` |
| PUT | /api/config/intent | 更新意图配置 | `{intents}` | `{success}` |
| GET | /api/config/legal-scope | 获取法律范围配置 | - | `{config}` |
| PUT | /api/config/legal-scope | 更新法律范围配置 | `{rules}` | `{success}` |
| GET | /api/config/reject-script | 获取拒绝话术 | - | `{script}` |
| PUT | /api/config/reject-script | 更新拒绝话术 | `{script}` | `{success}` |
| GET | /api/config/sensitive | 获取敏感信息配置 | - | `{config}` |
| PUT | /api/config/sensitive | 更新敏感信息配置 | `{types, rules}` | `{success}` |

---

## 6. 安全设计

### 6.1 认证授权

- **JWT Token**：有效期7天，包含用户ID、角色信息
- **角色区分**：C端用户(user) / B端管理员(admin)
- **权限控制**：API层面校验角色权限

### 6.2 数据安全

- **密码存储**：bcrypt加密，cost=12
- **敏感信息**：身份证、银行卡等自动脱敏
- **审计日志**：关键操作全部记录

### 6.3 API安全

- **CORS**：限制允许的域名
- **Rate Limiting**：防止滥用（MVP阶段可选）
- **输入校验**：Pydantic模型校验所有输入

---

## 7. 性能设计

### 7.1 响应时间目标

| 操作 | 目标时间 |
|------|----------|
| 用户登录 | < 500ms |
| 发送消息 | < 3s (首字节) |
| RAG检索 | < 1s |
| 合同生成 | < 2min |

### 7.2 优化策略

- **SSE流式响应**：首字节快速返回，提升用户体验
- **向量索引**：Chroma本地索引，检索速度快
- **配置缓存**：B端配置内存缓存，避免频繁查询
- **连接池**：SQLite使用连接池优化并发

---

## 8. 部署架构

### 8.1 Docker部署

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:///data/easyagent.db

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
```

### 8.2 数据目录挂载

```
/data/
├── templates/          # 合同模板
├── documents/          # 案例、审核规则等
├── rag_index/          # Chroma向量索引
├── contracts/          # 生成的合同文档
└── logs/               # 审计日志
```

---

## 9. 扩展性设计

### 9.1 后续版本规划

| 版本 | 功能扩展 | 架构调整 |
|------|----------|----------|
| V1.1 | 合同审核工作流 | 新增审核模块、工作流引擎 |
| V1.x | B端智能体对话 | 复用Agent模块，新增B端入口 |
| V2.0 | 多租户 | 数据库迁移PostgreSQL，新增租户隔离层 |

### 9.2 模块解耦

- **配置服务**：独立配置模块，支持热更新
- **Agent模块**：插件化设计，支持新增意图处理器
- **文档处理**：独立解析模块，支持新增文档格式

---

## 10. 附录

### 10.1 术语表

| 术语 | 说明 |
|------|------|
| SSE | Server-Sent Events，服务器推送事件 |
| RAG | Retrieval-Augmented Generation，检索增强生成 |
| Intent | 用户意图，如合同生成、知识查询等 |
| Chunk | 文档分块，用于向量索引 |
| Embedding | 文本向量表示 |

### 10.2 参考文档

- [FastAPI官方文档](https://fastapi.tiangolo.com/)
- [LangChain文档](https://python.langchain.com/)
- [Chroma文档](https://docs.trychroma.com/)
- [Ant Design文档](https://ant.design/)
