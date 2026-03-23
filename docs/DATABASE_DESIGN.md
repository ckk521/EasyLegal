# 智能合同审核平台 - 数据库设计

> 版本：V1.0
> 日期：2026-03-23
> 数据库：SQLite

---

## 1. 数据库概览

### 1.1 表清单

| 序号 | 表名 | 说明 | 数据量级 |
|------|------|------|----------|
| 1 | users | C端用户表 | 千级 |
| 2 | staff | B端员工表 | 十级 |
| 3 | chat_sessions | 对话会话表 | 万级 |
| 4 | chat_messages | 对话消息表 | 十万级 |
| 5 | contracts | 合同表 | 万级 |
| 6 | contract_data | 合同字段数据表 | 万级 |
| 7 | config_llm | 大模型配置表 | 1条 |
| 8 | config_embedding | Embedding配置表 | 1条 |
| 9 | config_intent | 核心意图配置表 | 十条 |
| 10 | config_legal_scope | 法律范围配置表 | 1条 |
| 11 | config_reject_script | 拒绝话术配置表 | 1条 |
| 12 | config_sensitive | 敏感信息配置表 | 十条 |
| 13 | templates | 合同模板表 | 十条 |
| 14 | field_definitions | 合同字段定义表 | 百条 |
| 15 | documents | 上传文档表 | 百条 |
| 16 | audit_logs | 审计日志表 | 十万级 |

### 1.2 ER图

```
┌─────────────┐       ┌──────────────────┐       ┌─────────────────┐
│   users     │       │  chat_sessions   │       │  chat_messages  │
│  (C端用户)   │       │                  │       │                 │
├─────────────┤       ├──────────────────┤       ├─────────────────┤
│ id (PK)     │◄──────│ user_id (FK)     │       │ session_id (FK) │
│ username    │       │ id (PK)          │◄──────│ id (PK)         │
│ password    │       │ contract_id (FK) │       │ role            │
│ nickname    │       │ title            │       │ content         │
│ status      │       │ created_at       │       │ created_at      │
│ created_at  │       │ updated_at       │       └─────────────────┘
└─────────────┘       └──────────────────┘
                              │
                              ▼
┌─────────────────┐   ┌──────────────────┐
│    contracts    │   │  contract_data   │
├─────────────────┤   ├──────────────────┤
│ id (PK)         │◄──│ contract_id (FK) │
│ user_id (FK)    │   │ field_name       │
│ session_id (FK) │   │ field_value      │
│ contract_no     │   │ field_type       │
│ contract_type   │   └──────────────────┘
│ status          │
│ content         │
│ file_path       │
│ created_at      │
│ updated_at      │
└─────────────────┘

┌─────────────────┐
│     staff       │
│   (B端员工)      │
├─────────────────┤
│ id (PK)         │
│ username        │
│ password        │
│ nickname        │
│ role            │─────── role: admin/operator/viewer
│ status          │
│ created_at      │
└─────────────────┘
         │
         │ 操作记录
         ▼
┌─────────────────┐
│   audit_logs    │
├─────────────────┤
│ id (PK)         │
│ user_id (FK)    │─────── staff.id
│ user_role       │
│ action          │
│ resource_type   │
│ resource_id     │
│ created_at      │
└─────────────────┘
```

---

## 2. 详细表结构

### 2.1 users - C端用户表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | 用户ID |
| username | VARCHAR(100) | UNIQUE, NOT NULL | 用户名/手机号/邮箱 |
| password | VARCHAR(255) | NOT NULL | 密码(bcrypt加密) |
| nickname | VARCHAR(50) | | 昵称 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | 状态: active/disabled |
| last_login_at | DATETIME | | 最后登录时间 |
| last_login_ip | VARCHAR(50) | | 最后登录IP |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引**：
```sql
CREATE UNIQUE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_status ON users(status);
```

---

### 2.2 staff - B端员工表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | 员工ID |
| username | VARCHAR(100) | UNIQUE, NOT NULL | 用户名 |
| password | VARCHAR(255) | NOT NULL | 密码(bcrypt加密) |
| nickname | VARCHAR(50) | | 昵称 |
| role | VARCHAR(20) | NOT NULL, DEFAULT 'operator' | 角色: admin/operator/viewer |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | 状态: active/disabled |
| first_login | BOOLEAN | DEFAULT 1 | 是否首次登录(需修改密码) |
| last_login_at | DATETIME | | 最后登录时间 |
| last_login_ip | VARCHAR(50) | | 最后登录IP |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**角色说明**：
| 角色 | 权限 |
|------|------|
| admin | 全部权限：用户管理、配置管理、系统管理 |
| operator | 运营权限：查看用户、查看对话、配置管理 |
| viewer | 只读权限：查看数据、查看配置 |

**索引**：
```sql
CREATE UNIQUE INDEX idx_staff_username ON staff(username);
CREATE INDEX idx_staff_role ON staff(role);
CREATE INDEX idx_staff_status ON staff(status);
```

**初始数据**：
```sql
-- 预设admin账号，密码: admin123 (bcrypt加密后)
INSERT INTO staff (username, password, nickname, role, first_login)
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5/Fs9WeBZa6yK', '超级管理员', 'admin', 0);
```

---

### 2.3 chat_sessions - 对话会话表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | 会话ID |
| user_id | INTEGER | NOT NULL, FK | 用户ID |
| contract_id | INTEGER | FK | 关联合同ID(可选) |
| title | VARCHAR(200) | | 会话标题 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | 状态: active/closed |
| intent_type | VARCHAR(50) | | 主要意图类型 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引**：
```sql
CREATE INDEX idx_sessions_user ON chat_sessions(user_id);
CREATE INDEX idx_sessions_contract ON chat_sessions(contract_id);
CREATE INDEX idx_sessions_status ON chat_sessions(status);
CREATE INDEX idx_sessions_created ON chat_sessions(created_at);
```

**外键**：
```sql
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE SET NULL;
```

---

### 2.4 chat_messages - 对话消息表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | 消息ID |
| session_id | INTEGER | NOT NULL, FK | 会话ID |
| role | VARCHAR(20) | NOT NULL | 角色: user/assistant/system |
| content | TEXT | NOT NULL | 消息内容 |
| intent | VARCHAR(50) | | 识别的意图 |
| metadata | JSON | | 元数据(字段提取结果等) |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引**：
```sql
CREATE INDEX idx_messages_session ON chat_messages(session_id);
CREATE INDEX idx_messages_created ON chat_messages(created_at);
```

**外键**：
```sql
FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE;
```

---

### 2.5 contracts - 合同表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | 合同ID |
| user_id | INTEGER | NOT NULL, FK | 用户ID |
| session_id | INTEGER | FK | 关联会话ID |
| contract_no | VARCHAR(50) | UNIQUE | 合同编号(自动生成) |
| contract_type | VARCHAR(50) | NOT NULL | 合同类型: lease/service/nda |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'draft' | 状态: draft/pending/completed |
| title | VARCHAR(200) | | 合同标题 |
| content | TEXT | | 合同内容(生成的最终文本) |
| file_path | VARCHAR(255) | | 导出文件路径 |
| ai_polish | BOOLEAN | DEFAULT 0 | 是否AI润色 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引**：
```sql
CREATE UNIQUE INDEX idx_contracts_no ON contracts(contract_no);
CREATE INDEX idx_contracts_user ON contracts(user_id);
CREATE INDEX idx_contracts_session ON contracts(session_id);
CREATE INDEX idx_contracts_status ON contracts(status);
CREATE INDEX idx_contracts_type ON contracts(contract_type);
```

**外键**：
```sql
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE SET NULL;
```

---

### 2.6 contract_data - 合同字段数据表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | ID |
| contract_id | INTEGER | NOT NULL, FK | 合同ID |
| field_name | VARCHAR(50) | NOT NULL | 字段名 |
| field_value | TEXT | | 字段值 |
| field_type | VARCHAR(20) | | 字段类型: string/date/number |
| is_required | BOOLEAN | DEFAULT 1 | 是否必填 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引**：
```sql
CREATE INDEX idx_contract_data_contract ON contract_data(contract_id);
CREATE UNIQUE INDEX idx_contract_data_field ON contract_data(contract_id, field_name);
```

**外键**：
```sql
FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE;
```

---

### 2.7 config_llm - 大模型配置表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | ID |
| api_key | VARCHAR(255) | | API密钥(加密存储) |
| base_url | VARCHAR(255) | | API地址 |
| model_name | VARCHAR(100) | | 模型名称 |
| temperature | DECIMAL(3,2) | DEFAULT 0.7 | 温度参数 |
| max_tokens | INTEGER | DEFAULT 2048 | 最大token数 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**说明**：MVP阶段只有一条记录

---

### 2.8 config_embedding - Embedding配置表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | ID |
| model_name | VARCHAR(100) | NOT NULL, DEFAULT 'm3e-base' | 模型名称 |
| chunk_size | INTEGER | DEFAULT 512 | 分块大小 |
| overlap | INTEGER | DEFAULT 50 | 重叠字符数 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

---

### 2.9 config_intent - 核心意图配置表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | ID |
| name | VARCHAR(50) | NOT NULL | 意图名称 |
| triggers | TEXT | | 触发词(逗号分隔) |
| description | TEXT | | 意图描述 |
| action | VARCHAR(50) | | 后续动作 |
| examples | TEXT | | 示例对话 |
| content | TEXT | | 完整.md内容 |
| priority | INTEGER | DEFAULT 0 | 优先级 |
| status | VARCHAR(20) | DEFAULT 'active' | 状态 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引**：
```sql
CREATE INDEX idx_intent_status ON config_intent(status);
```

**初始数据**：
```sql
INSERT INTO config_intent (name, triggers, description, action, priority) VALUES
('contract_generate', '生成合同,制作合同,起草合同,我要签合同,帮我写一份合同', '用户需要生成一份新的合同', 'contract_generate', 100),
('knowledge_query', '违约怎么办,合同条款解释,法律咨询,这个条款什么意思', '用户咨询法律相关问题', 'knowledge_query', 90),
('contract_status', '我的合同怎么样了,合同进度,之前的合同呢', '用户查询已创建合同的状态', 'contract_status', 80);
```

---

### 2.10 config_legal_scope - 法律范围配置表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | ID |
| content | TEXT | NOT NULL | 法律范围定义(.md格式) |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**初始数据**：
```sql
INSERT INTO config_legal_scope (content) VALUES
('# 法律问题范围

## 属于法律问题
- 合同相关：合同生成、合同审核、合同条款解释
- 法律法规：法律条款解释、法律责任
- 法律咨询：法律建议、权益保护

## 不属于法律问题
- 日常生活问题
- 娱乐休闲问题
- 技术操作问题
- 其他与法律无关的问题');
```

---

### 2.11 config_reject_script - 拒绝话术配置表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | ID |
| script | TEXT | NOT NULL | 拒绝话术 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**初始数据**：
```sql
INSERT INTO config_reject_script (script) VALUES
('我主要专注于法律和合同相关的问题，如果您有合同相关的需求，我很乐意帮助您。');
```

---

### 2.12 config_sensitive - 敏感信息配置表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | ID |
| type | VARCHAR(50) | NOT NULL | 类型: id_card/bank_card/address |
| name | VARCHAR(50) | NOT NULL | 显示名称 |
| pattern | VARCHAR(255) | | 正则表达式 |
| mask_rule | VARCHAR(50) | NOT NULL | 掩码规则: 前3后4/前4后4等 |
| status | VARCHAR(20) | DEFAULT 'active' | 状态 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**初始数据**：
```sql
INSERT INTO config_sensitive (type, name, pattern, mask_rule) VALUES
('id_card', '身份证号', '\\d{17}[\\dXx]', '前3后4'),
('bank_card', '银行卡号', '\\d{16,19}', '前4后4'),
('address', '地址', NULL, '保留省市区');
```

---

### 2.13 templates - 合同模板表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | ID |
| name | VARCHAR(100) | NOT NULL | 模板名称 |
| file_path | VARCHAR(255) | NOT NULL | 文件路径 |
| file_type | VARCHAR(20) | NOT NULL | 文件类型: pdf/word/md/text |
| contract_type | VARCHAR(50) | NOT NULL | 合同类型 |
| content | TEXT | | 解析后的模板内容 |
| status | VARCHAR(20) | DEFAULT 'active' | 状态 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引**：
```sql
CREATE INDEX idx_templates_type ON templates(contract_type);
CREATE INDEX idx_templates_status ON templates(status);
```

---

### 2.14 field_definitions - 合同字段定义表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | ID |
| template_id | INTEGER | FK | 模板ID(可选) |
| contract_type | VARCHAR(50) | NOT NULL | 合同类型 |
| field_name | VARCHAR(50) | NOT NULL | 字段名 |
| field_label | VARCHAR(100) | NOT NULL | 字段标签(显示名) |
| field_type | VARCHAR(20) | DEFAULT 'string' | 字段类型: string/date/number/select |
| is_required | BOOLEAN | DEFAULT 1 | 是否必填 |
| default_value | VARCHAR(255) | | 默认值 |
| options | JSON | | 选项(select类型) |
| field_order | INTEGER | DEFAULT 0 | 字段顺序 |
| validation | VARCHAR(255) | | 验证规则 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引**：
```sql
CREATE INDEX idx_field_def_type ON field_definitions(contract_type);
CREATE INDEX idx_field_def_template ON field_definitions(template_id);
```

**初始数据**（租赁合同）：
```sql
INSERT INTO field_definitions (contract_type, field_name, field_label, field_type, is_required, field_order) VALUES
('lease', 'contract_type', '合同类型', 'select', 1, 1),
('lease', 'sign_date', '签订日期', 'date', 1, 2),
('lease', 'effective_date', '生效日期', 'date', 1, 3),
('lease', 'expire_date', '失效日期', 'date', 1, 4),
('lease', 'party_a_name', '甲方名称', 'string', 1, 5),
('lease', 'party_a_contact', '甲方联系方式', 'string', 1, 6),
('lease', 'party_a_address', '甲方地址', 'string', 0, 7),
('lease', 'party_b_name', '乙方名称', 'string', 1, 8),
('lease', 'party_b_contact', '乙方联系方式', 'string', 1, 9),
('lease', 'party_b_address', '乙方地址', 'string', 0, 10),
('lease', 'lease_subject', '租赁标的', 'string', 1, 11),
('lease', 'lease_address', '租赁地址', 'string', 1, 12),
('lease', 'rent_amount', '租金金额', 'number', 1, 13),
('lease', 'payment_method', '支付方式', 'select', 1, 14),
('lease', 'deposit_amount', '押金金额', 'number', 1, 15),
('lease', 'deposit_return', '押金退还条件', 'string', 0, 16);
```

---

### 2.15 documents - 上传文档表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | ID |
| name | VARCHAR(100) | NOT NULL | 文档名称 |
| file_path | VARCHAR(255) | NOT NULL | 文件路径 |
| file_type | VARCHAR(20) | NOT NULL | 文件类型 |
| doc_type | VARCHAR(50) | NOT NULL | 文档类型: case/audit_rule/intent_doc |
| content | TEXT | | 解析后的文本内容 |
| indexed | BOOLEAN | DEFAULT 0 | 是否已建立向量索引 |
| status | VARCHAR(20) | DEFAULT 'active' | 状态 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引**：
```sql
CREATE INDEX idx_documents_type ON documents(doc_type);
CREATE INDEX idx_documents_indexed ON documents(indexed);
```

---

### 2.16 audit_logs - 审计日志表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | ID |
| user_id | INTEGER | | 操作用户ID |
| user_role | VARCHAR(20) | | 用户角色 |
| action | VARCHAR(50) | NOT NULL | 操作类型 |
| resource_type | VARCHAR(50) | | 资源类型 |
| resource_id | INTEGER | | 资源ID |
| detail | JSON | | 操作详情 |
| ip_address | VARCHAR(50) | | IP地址 |
| user_agent | VARCHAR(255) | | 用户代理 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引**：
```sql
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at);
```

**操作类型枚举**：
```python
AUDIT_ACTIONS = [
    'user_register',      # 用户注册
    'user_login',         # 用户登录
    'user_logout',        # 用户登出
    'user_status_change', # 用户状态变更
    'user_delete',        # 用户删除
    'chat_send',          # 发送消息
    'chat_delete',        # 删除消息
    'contract_create',    # 创建合同
    'contract_update',    # 更新合同
    'contract_generate',  # 生成合同
    'contract_export',    # 导出合同
    'contract_delete',    # 删除合同
    'config_update',      # 配置更新
    'file_upload',        # 文件上传
    'file_delete',        # 文件删除
]
```

---

## 3. 完整建表SQL

```sql
-- 创建数据库文件
-- SQLite会自动创建

-- 启用外键约束
PRAGMA foreign_keys = ON;

-- 1. C端用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    nickname VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    last_login_at DATETIME,
    last_login_ip VARCHAR(50),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);

-- 2. B端员工表
CREATE TABLE IF NOT EXISTS staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    nickname VARCHAR(50),
    role VARCHAR(20) NOT NULL DEFAULT 'operator',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    first_login BOOLEAN DEFAULT 1,
    last_login_at DATETIME,
    last_login_ip VARCHAR(50),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_staff_username ON staff(username);
CREATE INDEX IF NOT EXISTS idx_staff_role ON staff(role);
CREATE INDEX IF NOT EXISTS idx_staff_status ON staff(status);

-- 3. 合同模板表
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    contract_type VARCHAR(50) NOT NULL,
    content TEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_templates_type ON templates(contract_type);
CREATE INDEX IF NOT EXISTS idx_templates_status ON templates(status);

-- 4. 合同字段定义表
CREATE TABLE IF NOT EXISTS field_definitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER,
    contract_type VARCHAR(50) NOT NULL,
    field_name VARCHAR(50) NOT NULL,
    field_label VARCHAR(100) NOT NULL,
    field_type VARCHAR(20) DEFAULT 'string',
    is_required BOOLEAN DEFAULT 1,
    default_value VARCHAR(255),
    options JSON,
    field_order INTEGER DEFAULT 0,
    validation VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_field_def_type ON field_definitions(contract_type);
CREATE INDEX IF NOT EXISTS idx_field_def_template ON field_definitions(template_id);

-- 5. 合同表
CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id INTEGER,
    contract_no VARCHAR(50) UNIQUE,
    contract_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    title VARCHAR(200),
    content TEXT,
    file_path VARCHAR(255),
    ai_polish BOOLEAN DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_contracts_no ON contracts(contract_no);
CREATE INDEX IF NOT EXISTS idx_contracts_user ON contracts(user_id);
CREATE INDEX IF NOT EXISTS idx_contracts_session ON contracts(session_id);
CREATE INDEX IF NOT EXISTS idx_contracts_status ON contracts(status);
CREATE INDEX IF NOT EXISTS idx_contracts_type ON contracts(contract_type);

-- 6. 合同字段数据表
CREATE TABLE IF NOT EXISTS contract_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    field_name VARCHAR(50) NOT NULL,
    field_value TEXT,
    field_type VARCHAR(20),
    is_required BOOLEAN DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_contract_data_contract ON contract_data(contract_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_contract_data_field ON contract_data(contract_id, field_name);

-- 7. 对话会话表
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    contract_id INTEGER,
    title VARCHAR(200),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    intent_type VARCHAR(50),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_contract ON chat_sessions(contract_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON chat_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON chat_sessions(created_at);

-- 8. 对话消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    intent VARCHAR(50),
    metadata JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON chat_messages(created_at);

-- 9. 大模型配置表
CREATE TABLE IF NOT EXISTS config_llm (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key VARCHAR(255),
    base_url VARCHAR(255),
    model_name VARCHAR(100),
    temperature DECIMAL(3,2) DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 2048,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 10. Embedding配置表
CREATE TABLE IF NOT EXISTS config_embedding (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name VARCHAR(100) NOT NULL DEFAULT 'm3e-base',
    chunk_size INTEGER DEFAULT 512,
    overlap INTEGER DEFAULT 50,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 11. 核心意图配置表
CREATE TABLE IF NOT EXISTS config_intent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL,
    triggers TEXT,
    description TEXT,
    action VARCHAR(50),
    examples TEXT,
    content TEXT,
    priority INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_intent_status ON config_intent(status);

-- 12. 法律范围配置表
CREATE TABLE IF NOT EXISTS config_legal_scope (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 13. 拒绝话术配置表
CREATE TABLE IF NOT EXISTS config_reject_script (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script TEXT NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 14. 敏感信息配置表
CREATE TABLE IF NOT EXISTS config_sensitive (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type VARCHAR(50) NOT NULL,
    name VARCHAR(50) NOT NULL,
    pattern VARCHAR(255),
    mask_rule VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 15. 上传文档表
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    content TEXT,
    indexed BOOLEAN DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_indexed ON documents(indexed);

-- 16. 审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    user_role VARCHAR(20),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    detail JSON,
    ip_address VARCHAR(50),
    user_agent VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
```

---

## 4. 初始数据

```sql
-- 预设admin账号 (密码: admin123) - 存入staff表
INSERT INTO staff (username, password, nickname, role, first_login) VALUES
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5/Fs9WeBZa6yK', '超级管理员', 'admin', 0);

-- 预置意图配置
INSERT INTO config_intent (name, triggers, description, action, priority) VALUES
('contract_generate', '生成合同,制作合同,起草合同,我要签合同,帮我写一份合同', '用户需要生成一份新的合同', 'contract_generate', 100),
('knowledge_query', '违约怎么办,合同条款解释,法律咨询,这个条款什么意思', '用户咨询法律相关问题', 'knowledge_query', 90),
('contract_status', '我的合同怎么样了,合同进度,之前的合同呢', '用户查询已创建合同的状态', 'contract_status', 80);

-- 预置法律范围
INSERT INTO config_legal_scope (content) VALUES
('# 法律问题范围

## 属于法律问题
- 合同相关：合同生成、合同审核、合同条款解释
- 法律法规：法律条款解释、法律责任
- 法律咨询：法律建议、权益保护

## 不属于法律问题
- 日常生活问题
- 娱乐休闲问题
- 技术操作问题
- 其他与法律无关的问题');

-- 预置拒绝话术
INSERT INTO config_reject_script (script) VALUES
('我主要专注于法律和合同相关的问题，如果您有合同相关的需求，我很乐意帮助您。');

-- 预置敏感信息规则
INSERT INTO config_sensitive (type, name, pattern, mask_rule) VALUES
('id_card', '身份证号', '\d{17}[\dXx]', '前3后4'),
('bank_card', '银行卡号', '\d{16,19}', '前4后4'),
('address', '地址', NULL, '保留省市区');

-- 预置租赁合同字段定义
INSERT INTO field_definitions (contract_type, field_name, field_label, field_type, is_required, field_order) VALUES
('lease', 'contract_type', '合同类型', 'select', 1, 1),
('lease', 'sign_date', '签订日期', 'date', 1, 2),
('lease', 'effective_date', '生效日期', 'date', 1, 3),
('lease', 'expire_date', '失效日期', 'date', 1, 4),
('lease', 'party_a_name', '甲方名称', 'string', 1, 5),
('lease', 'party_a_contact', '甲方联系方式', 'string', 1, 6),
('lease', 'party_a_address', '甲方地址', 'string', 0, 7),
('lease', 'party_b_name', '乙方名称', 'string', 1, 8),
('lease', 'party_b_contact', '乙方联系方式', 'string', 1, 9),
('lease', 'party_b_address', '乙方地址', 'string', 0, 10),
('lease', 'lease_subject', '租赁标的', 'string', 1, 11),
('lease', 'lease_address', '租赁地址', 'string', 1, 12),
('lease', 'rent_amount', '租金金额', 'number', 1, 13),
('lease', 'payment_method', '支付方式', 'select', 1, 14),
('lease', 'deposit_amount', '押金金额', 'number', 1, 15),
('lease', 'deposit_return', '押金退还条件', 'string', 0, 16);

-- 预置Embedding配置
INSERT INTO config_embedding (model_name, chunk_size, overlap) VALUES
('m3e-base', 512, 50);
```

---

## 5. 数据库维护

### 5.1 备份策略

```bash
# 每日备份脚本
sqlite3 data/app.db ".backup 'data/backup/app_$(date +%Y%m%d).db'"
```

### 5.2 性能优化

```sql
-- 启用WAL模式
PRAGMA journal_mode=WAL;

-- 设置缓存大小
PRAGMA cache_size=10000;

-- 设置同步模式
PRAGMA synchronous=NORMAL;

-- 设置临时存储
PRAGMA temp_store=MEMORY;
```

### 5.3 定期清理

```sql
-- 清理3个月前的审计日志
DELETE FROM audit_logs WHERE created_at < datetime('now', '-3 months');

-- 清理已关闭超过6个月的会话
DELETE FROM chat_sessions WHERE status = 'closed' AND updated_at < datetime('now', '-6 months');
```
