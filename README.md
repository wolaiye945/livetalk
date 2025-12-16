# LiveTalk

Web版实时语音对话系统，支持与LMStudio大模型进行语音/文字实时对话。

## 功能特性

- 🎙️ 实时语音对话（按住说话模式）
- 💬 文字聊天（支持Markdown渲染和代码高亮）
- 🔐 多用户支持（用户名密码认证）
- 📁 对话分组管理
- 🔍 历史对话搜索
- 📝 自动上下文压缩（支持长时间对话）
- 🏷️ 对话自动总结和标签
- 📤 对话导出（JSON/Markdown）
- 🌓 亮色/暗色主题切换
- 📱 PC和移动端适配

## 技术栈

- **前端**: React 18 + TypeScript + Vite + TailwindCSS
- **后端**: Python 3.11 + FastAPI + SQLAlchemy
- **数据库**: SQLite
- **语音识别**: faster-whisper (本地)
- **语音合成**: Piper TTS (本地)
- **LLM**: LMStudio (OpenAI兼容API)

## 快速开始

### 前置要求

- Node.js 18+
- Python 3.11+
- LMStudio (已启动并加载模型，默认端口1234)

### 安装

1. 克隆项目
```bash
git clone <repo-url>
cd livetalk
```

2. 安装后端依赖
```bash
cd backend
pip install -r requirements.txt
```

3. 安装前端依赖
```bash
cd frontend
npm install
```

### 下载语音模型（可选，用于语音功能）

**Whisper模型（语音识别）**：
- faster-whisper会自动下载模型，首次运行时会下载到缓存目录
- 也可手动下载放到 `backend/models/whisper/`

**Piper TTS模型（语音合成）**：
- 下载中文模型：https://github.com/rhasspy/piper/releases
- 推荐下载：`zh_CN-huayan-medium.onnx` 及对应的 `.onnx.json` 配置文件
- 放到 `backend/models/piper/` 目录

### 配置

编辑 `backend/config.yaml` 配置LMStudio地址和其他参数：

```yaml
llm:
  main_model:
    base_url: "http://localhost:1234/v1"  # LMStudio API地址
    api_key: "lm-studio"
    model: "default"
```

### 启动

**方式一：分别启动**

1. 启动后端（在backend目录）
```bash
cd backend
python -m app.main
```

2. 启动前端（在frontend目录）
```bash
cd frontend
npm run dev
```

**方式二：使用脚本启动（推荐）**

Windows:
```powershell
# 在项目根目录
cd backend; Start-Process python -ArgumentList "-m", "app.main"
cd ..\frontend; npm run dev
```

3. 打开浏览器访问 http://localhost:5173

### 首次使用

1. 注册账号（第一个注册的用户自动成为管理员）
2. 创建新对话
3. 开始聊天（文字或语音）

## 项目结构

```
livetalk/
├── frontend/                # React前端
│   ├── src/
│   │   ├── components/      # UI组件
│   │   ├── hooks/           # 自定义Hooks
│   │   ├── services/        # API服务
│   │   ├── stores/          # 状态管理(Zustand)
│   │   └── types/           # TypeScript类型
│   └── package.json
├── backend/                 # Python后端
│   ├── app/
│   │   ├── api/             # API路由
│   │   ├── core/            # 核心模块(配置/安全/数据库)
│   │   ├── models/          # 数据模型
│   │   ├── services/        # 业务逻辑
│   │   └── schemas/         # Pydantic模型
│   ├── models/              # AI模型文件目录
│   ├── data/                # 数据目录
│   ├── config.yaml          # 配置文件
│   └── requirements.txt
├── DESIGN.md                # 设计文档
└── README.md                # 本文件
```

## API文档

启动后端后，访问 http://localhost:8000/docs 查看完整的API文档（Swagger UI）

## 配置说明

### 上下文压缩

```yaml
context:
  max_tokens: 4096           # 上下文最大token数
  compression_threshold: 0.8  # 达到80%时触发压缩
```

### 语音设置

```yaml
stt:
  model_size: "base"         # whisper模型大小: tiny/base/small/medium/large
  language: "zh"             # 语言代码

tts:
  model: "zh_CN-huayan-medium"  # piper模型名称
  length_scale: 1.0          # 语速，1.0为正常
```

## 常见问题

**Q: LMStudio连接失败？**
A: 确保LMStudio已启动，且在设置中开启了"Server"功能，默认端口1234

**Q: 语音功能不工作？**
A: 1) 确保浏览器允许麦克风权限；2) 检查是否已下载并配置Piper模型

**Q: 如何重置管理员密码？**
A: 删除 `backend/data/livetalk.db` 数据库文件后重新注册

## 许可证

MIT
