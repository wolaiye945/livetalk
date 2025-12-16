# LiveTalk - Web版实时语音对话系统

## 项目概述

基于 React + Python 的实时语音对话 Web 应用，连接 LMStudio 大模型后端，支持多用户、上下文压缩、对话管理等功能。

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| 前端 | React 18 + TypeScript + Vite |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy |
| 数据库 | SQLite |
| STT | faster-whisper (本地离线) |
| TTS | Piper (本地离线) |
| LLM | LMStudio (OpenAI兼容API) |
| 实时通信 | WebSocket |

## 项目结构

```
livetalk/
├── frontend/                   # React前端
│   ├── public/
│   ├── src/
│   │   ├── components/         # UI组件
│   │   │   ├── Chat/           # 对话相关组件
│   │   │   ├── Voice/          # 语音相关组件
│   │   │   ├── Layout/         # 布局组件
│   │   │   └── Common/         # 通用组件
│   │   ├── hooks/              # 自定义Hooks
│   │   ├── services/           # API服务
│   │   ├── stores/             # 状态管理(Zustand)
│   │   ├── styles/             # 全局样式
│   │   ├── types/              # TypeScript类型
│   │   ├── utils/              # 工具函数
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── backend/                    # Python后端
│   ├── app/
│   │   ├── api/                # API路由
│   │   │   ├── auth.py         # 认证接口
│   │   │   ├── chat.py         # 对话接口
│   │   │   ├── voice.py        # 语音接口
│   │   │   ├── conversation.py # 对话管理接口
│   │   │   └── admin.py        # 管理员接口
│   │   ├── core/               # 核心模块
│   │   │   ├── config.py       # 配置管理
│   │   │   ├── security.py     # 安全/JWT
│   │   │   └── database.py     # 数据库连接
│   │   ├── models/             # 数据模型
│   │   │   ├── user.py
│   │   │   ├── conversation.py
│   │   │   └── message.py
│   │   ├── services/           # 业务逻辑
│   │   │   ├── llm_service.py  # LLM对话服务
│   │   │   ├── stt_service.py  # 语音转文字
│   │   │   ├── tts_service.py  # 文字转语音
│   │   │   ├── context_service.py  # 上下文管理
│   │   │   └── summary_service.py  # 总结服务
│   │   ├── schemas/            # Pydantic模型
│   │   └── main.py             # 应用入口
│   ├── models/                 # AI模型文件目录
│   │   ├── whisper/            # Whisper模型
│   │   └── piper/              # Piper语音模型
│   ├── data/                   # 数据目录
│   │   └── livetalk.db         # SQLite数据库
│   ├── requirements.txt
│   └── config.yaml             # 配置文件
│
├── DESIGN.md                   # 本设计文档
└── README.md                   # 项目说明
```

## 数据库设计

### users 用户表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| username | VARCHAR(50) UNIQUE | 用户名 |
| password_hash | VARCHAR(255) | 密码哈希 |
| role | VARCHAR(20) | 角色: user/admin |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### conversations 对话组表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| user_id | INTEGER FK | 用户ID |
| title | VARCHAR(200) | 对话标题 |
| tags | JSON | 标签数组 |
| summary | TEXT | 对话摘要 |
| context_summary | TEXT | 压缩后的上下文摘要 |
| group_name | VARCHAR(100) | 分组名称 |
| is_archived | BOOLEAN | 是否归档 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### messages 消息表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| conversation_id | INTEGER FK | 对话ID |
| role | VARCHAR(20) | 角色: user/assistant/system |
| content | TEXT | 消息内容 |
| audio_path | VARCHAR(500) | 音频文件路径(可选) |
| token_count | INTEGER | Token数量 |
| created_at | DATETIME | 创建时间 |

### conversation_groups 对话分组表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| user_id | INTEGER FK | 用户ID |
| name | VARCHAR(100) | 分组名称 |
| order_index | INTEGER | 排序索引 |
| created_at | DATETIME | 创建时间 |

## API设计

### 认证接口
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/refresh` - 刷新Token
- `GET /api/auth/me` - 获取当前用户信息

### 对话接口
- `GET /api/conversations` - 获取对话列表(支持分页、搜索、分组筛选)
- `POST /api/conversations` - 创建新对话
- `GET /api/conversations/{id}` - 获取对话详情
- `PUT /api/conversations/{id}` - 更新对话(标题、分组、标签)
- `DELETE /api/conversations/{id}` - 删除对话
- `POST /api/conversations/{id}/archive` - 归档对话
- `GET /api/conversations/{id}/export` - 导出对话(JSON/Markdown)
- `DELETE /api/conversations/batch` - 批量删除对话

### 消息接口
- `GET /api/conversations/{id}/messages` - 获取消息历史
- `POST /api/conversations/{id}/messages` - 发送文字消息
- `WebSocket /ws/chat/{conversation_id}` - 实时对话WebSocket

### 语音接口
- `POST /api/voice/stt` - 语音转文字
- `POST /api/voice/tts` - 文字转语音
- `WebSocket /ws/voice/{conversation_id}` - 实时语音WebSocket

### 分组接口
- `GET /api/groups` - 获取分组列表
- `POST /api/groups` - 创建分组
- `PUT /api/groups/{id}` - 更新分组
- `DELETE /api/groups/{id}` - 删除分组

### 管理员接口
- `GET /api/admin/users` - 获取所有用户
- `GET /api/admin/users/{id}/conversations` - 获取指定用户的对话
- `DELETE /api/admin/users/{id}` - 删除用户
- `GET /api/admin/stats` - 系统统计信息

## 核心流程

### 1. 实时语音对话流程
```
用户按住说话 → 录制音频 → WebSocket发送 → 
faster-whisper STT → 文字 → LLM处理 → 
回复文字 → Piper TTS → 音频 → WebSocket返回 → 播放
```

### 2. 上下文压缩流程
```
发送消息前检查token数 → 超过阈值(默认4K) → 
调用轻量模型总结历史消息 → 生成摘要替换旧消息 → 
继续对话
```

### 3. 对话结束总结流程
```
用户结束对话/切换对话 → 调用LLM总结对话要点 → 
生成标签 → 存储到conversation.summary和tags → 
下次继续时加载摘要作为上下文
```

## 配置文件示例 (config.yaml)

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  cors_origins: ["http://localhost:5173"]

database:
  url: "sqlite:///./data/livetalk.db"

auth:
  secret_key: "your-secret-key-change-in-production"
  algorithm: "HS256"
  access_token_expire_minutes: 1440  # 24小时

llm:
  main_model:
    base_url: "http://localhost:1234/v1"
    api_key: "lm-studio"
    model: "default"  # LMStudio中加载的模型
    max_tokens: 2048
  summary_model:
    base_url: "http://localhost:1234/v1"  # 可独立配置
    api_key: "lm-studio"
    model: "default"
    max_tokens: 1024

context:
  max_tokens: 4096  # 上下文最大token数
  compression_threshold: 0.8  # 达到80%时触发压缩
  summary_prompt: |
    请总结以下对话的要点，保留关键信息，输出简洁的摘要：

stt:
  model_path: "./models/whisper/ggml-base.bin"
  language: "zh"
  
tts:
  model_path: "./models/piper/zh_CN-huayan-medium.onnx"
  config_path: "./models/piper/zh_CN-huayan-medium.onnx.json"
  speaker_id: 0

voice:
  mode: "push_to_talk"  # push_to_talk / vad (预留)
  vad_threshold: 0.5    # VAD模式阈值(预留)
```

## 前端页面设计

### 1. 登录/注册页
- 用户名密码表单
- 记住登录状态

### 2. 主界面布局
```
┌─────────────────────────────────────────────────┐
│  Logo    搜索框         用户头像  主题切换  设置  │
├──────────┬──────────────────────────────────────┤
│ 分组列表  │                                      │
│ ├ 工作   │         对话内容区域                  │
│ │ └对话1 │                                      │
│ │ └对话2 │    [消息气泡 - Markdown渲染]         │
│ ├ 学习   │    [消息气泡 - 代码高亮]             │
│ └ 未分组 │                                      │
│          │                                      │
│ [新建对话]│──────────────────────────────────────│
│          │  [🎤 按住说话]  [文字输入框]  [发送]  │
└──────────┴──────────────────────────────────────┘
```

### 3. 移动端布局
- 侧边栏改为抽屉式
- 底部固定语音/输入区
- 全屏对话模式

### 4. 设置页面
- 个人信息修改
- 密码修改
- LLM配置（管理员可见全局配置）
- 上下文长度设置
- 语音设置（语速、音色等）
- 主题设置

## 开发计划

### Phase 1: 基础框架 (Day 1-2)
- [ ] 初始化项目结构
- [ ] 后端FastAPI框架搭建
- [ ] 数据库模型和迁移
- [ ] 用户认证系统
- [ ] 前端React项目初始化
- [ ] 基础UI组件和路由

### Phase 2: 核心对话功能 (Day 3-4)
- [ ] LLM服务集成
- [ ] 文字对话功能
- [ ] WebSocket实时通信
- [ ] 对话历史管理
- [ ] Markdown渲染和代码高亮

### Phase 3: 语音功能 (Day 5-6)
- [ ] faster-whisper集成
- [ ] Piper TTS集成
- [ ] 按住说话录音组件
- [ ] 语音实时处理流程

### Phase 4: 高级功能 (Day 7-8)
- [ ] 上下文压缩功能
- [ ] 对话总结和标签
- [ ] 搜索功能
- [ ] 对话分组管理
- [ ] 导出功能

### Phase 5: 完善和优化 (Day 9-10)
- [ ] 管理员功能
- [ ] 主题切换
- [ ] 移动端适配优化
- [ ] 性能优化
- [ ] 测试和Bug修复
