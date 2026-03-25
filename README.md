# DOTA2 RAG 知识问答系统

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-0.1+-yellow.svg)](https://langchain.com)
[![License](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)

基于 RAG（检索增强生成）技术的 DOTA2 智能知识问答系统，支持英雄、物品、技能、版本更新等全方位游戏知识查询。

[功能特性](#功能特性) • [快速开始](#快速开始) • [项目结构](#项目结构) • [API 文档](#api-文档) • [开发指南](#开发指南)

</div>

---

## 📖 目录

- [功能特性](#功能特性)
- [技术架构](#技术架构)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [配置说明](#配置说明)
- [数据采集](#数据采集)
- [API 文档](#api-文档)
- [前端界面](#前端界面)
- [部署指南](#部署指南)
- [开发指南](#开发指南)
- [常见问题](#常见问题)

---

## ✨ 功能特性

### 核心功能
- 🤖 **智能问答**：基于 RAG 技术的自然语言问答，准确理解用户意图
- 📚 **海量知识库**：覆盖 127+ 英雄、544+ 物品、2706+ 技能、5060+ 版本更新条目
- 🔄 **自动更新**：支持自动抓取最新版本数据（当前支持 7.41 版本）
- 🎯 **精准检索**：基于向量相似度的智能文档检索，支持语义搜索
- ⚡ **高性能**：异步处理架构，支持并发请求
- 🌐 **Web 界面**：现代化的前端交互界面

### 数据来源
- **Wiki 数据**：游戏机制、背景故事等详细信息
- **英雄数据**：全英雄属性、技能、成长数据
- **物品数据**：装备属性、合成配方、效果说明
- **技能数据**：技能详情、冷却时间、魔法消耗
- **版本更新**：历史版本更新日志和 Patch Notes

---

## 🏗️ 技术架构

### 技术栈
- **后端框架**：FastAPI - 高性能异步 Web 框架
- **RAG 引擎**：LangChain - 构建 RAG 应用的核心框架
- **向量数据库**：ChromaDB - 高效的嵌入向量存储与检索
- **LLM 平台**：支持阿里云通义千问（DashScope）/ 硅基流动等 OpenAI 兼容平台
- **数据处理**：BeautifulSoup4、HTTPX - 网页抓取和数据解析
- **配置管理**：Pydantic Settings - 类型安全的配置管理

### 系统架构

```
┌─────────────┐
│   用户请求   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  FastAPI 服务   │ ◄─── CORS、日志、异常处理
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────┐  ┌─────────┐
│问答  │  │数据采集 │
│路由  │  │路由     │
└──┬──┘  └────┬────┘
   │          │
   ▼          ▼
┌──────────┐ ┌──────────┐
│ RAG 链   │ │采集引擎  │
│          │ │          │
│ · 检索器 │ │ · Wiki   │
│ · 提示词 │ │ · Heroes │
│ · LLM    │ │ · Items  │
└────┬─────┘ │ · Patches│
     │       └────┬─────┘
     │            │
     ▼            ▼
┌──────────────────┐
│   ChromaDB       │
│  (向量存储)       │
└──────────────────┘
     │
     ▼
┌──────────────────┐
│  持久化存储       │
│ data/chroma_db   │
└──────────────────┘
```

---

## 🚀 快速开始

### 环境要求
- Python 3.11+
- 阿里云 DashScope API Key（或其他 OpenAI 兼容平台 API Key）

### 1. 克隆项目

```bash
git clone <repository-url>
cd DOTA2RAG
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制示例配置文件并编辑：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key：

```bash
# 必需配置
DASHSCOPE_API_KEY=your_api_key_here

# 可选配置（使用默认值即可）
API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v3
CHAT_MODEL=qwen-plus
```

### 4. 采集数据（首次运行）

```bash
python -m src.ingestion.runner
```

首次采集大约需要 5-10 分钟，会自动下载并处理所有游戏数据。

### 5. 启动 API 服务

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. 访问服务

- **API 文档**：http://localhost:8000/docs
- **服务状态**：http://localhost:8000/api/health
- **前端界面**：打开 `frontend/index.html`

### 7. 测试问答

```bash
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "影魔有什么技能？"}'
```

---

## 📁 项目结构

```
DOTA2RAG/
├── config/                      # 配置模块
│   └── settings.py             # 环境变量配置管理
│
├── src/                        # 源代码目录
│   ├── api/                    # FastAPI 应用
│   │   ├── main.py            # 应用入口和路由注册
│   │   ├── schemas.py         # Pydantic 数据模型
│   │   └── routes/            # API 路由
│   │       ├── ask.py         # 问答接口
│   │       ├── ingest.py      # 数据采集接口
│   │       └── health.py      # 健康检查接口
│   │
│   ├── ingestion/              # 数据采集模块
│   │   ├── runner.py          # 采集任务运行器
│   │   ├── version_tracker.py # 版本追踪管理
│   │   ├── sources/           # 数据源
│   │   │   ├── wiki.py        # Wiki 数据抓取
│   │   │   ├── heroes.py      # 英雄数据
│   │   │   ├── items.py       # 物品数据
│   │   │   ├── abilities.py   # 技能数据
│   │   │   ├── patches.py     # 版本数据管理
│   │   │   └── patch_scraper.py # Patch Notes 爬虫
│   │   └── processors/        # 数据处理器
│   │       ├── chunker.py     # 文档分块
│   │       └── cleaner.py     # 数据清洗
│   │
│   ├── rag/                    # RAG 核心模块
│   │   ├── chain.py           # RAG 链构建
│   │   ├── prompts.py         # 提示词模板
│   │   └── retriever.py       # 检索器实现
│   │
│   └── vectorstore/            # 向量存储模块
│       ├── embeddings.py      # 嵌入模型封装
│       └── store.py           # ChromaDB 存储管理
│
├── data/                       # 数据目录
│   ├── chroma_db/             # ChromaDB 持久化数据
│   └── version_meta.json      # 版本元数据
│
├── frontend/                   # 前端界面
│   ├── index.html             # Web 界面
│   └── README.md              # 前端文档
│
├── openspec/                   # OpenSpec 规范文档
│   ├── specs/                 # 模块规范
│   └── changes/               # 变更记录
│
├── .env.example               # 环境变量示例
├── requirements.txt           # Python 依赖
├── Dockerfile                 # Docker 构建文件
└── README.md                  # 项目文档
```

---

## ⚙️ 配置说明

### 环境变量详解

| 变量名 | 说明 | 默认值 | 是否必需 |
|--------|------|--------|----------|
| `DASHSCOPE_API_KEY` | API 平台密钥 | - | ✅ 必需 |
| `API_BASE_URL` | API 服务地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | ❌ 可选 |
| `EMBEDDING_MODEL` | 嵌入模型名称 | `text-embedding-v3` | ❌ 可选 |
| `CHAT_MODEL` | 聊天模型名称 | `qwen-plus` | ❌ 可选 |
| `CHROMA_PERSIST_DIR` | 向量数据库存储目录 | `data/chroma_db` | ❌ 可选 |
| `API_HOST` | API 服务监听地址 | `0.0.0.0` | ❌ 可选 |
| `API_PORT` | API 服务端口 | `8000` | ❌ 可选 |
| `CACHE_TTL` | 缓存过期时间（秒） | `3600` | ❌ 可选 |
| `LOG_LEVEL` | 日志级别 | `INFO` | ❌ 可选 |

### 支持的 API 平台

本项目支持所有兼容 OpenAI API 格式的平台：

#### 1. 阿里云 DashScope（通义千问）
```bash
API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v3
CHAT_MODEL=qwen-plus
```

#### 2. 硅基流动
```bash
API_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct
```

#### 3. 其他 OpenAI 兼容平台
只需修改 `API_BASE_URL` 和对应的模型名称即可。

---

## 📥 数据采集

### 手动触发数据采集

#### 方式 1：命令行运行
```bash
python -m src.ingestion.runner
```

#### 方式 2：通过 API
```bash
curl -X POST "http://localhost:8000/api/ingest" \
  -H "Content-Type: application/json" \
  -d '{"full_reload": false}'
```

### 采集参数说明

- `full_reload=false`（默认）：增量更新，仅采集新数据
- `full_reload=true`：完全重建，清空并重新采集所有数据

### 数据统计

查看当前数据库统计信息：

```bash
curl http://localhost:8000/api/stats
```

响应示例：
```json
{
  "last_updated": "2026-03-25T15:06:48",
  "game_version": "7.41",
  "sources": {
    "wiki": {"count": 22},
    "heroes": {"count": 127},
    "items": {"count": 544},
    "abilities": {"count": 2706},
    "patches": {"count": 5060}
  },
  "vector_stats": {
    "total_documents": 8459,
    "collections": ["dota2_knowledge"]
  }
}
```

---

## 📡 API 文档

### 1. 问答接口

**POST** `/api/ask`

提交问题并获取 AI 回答。

#### 请求参数

```json
{
  "question": "影魔的技能有哪些？",
  "stream": false,
  "top_k": 5
}
```

| 字段 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `question` | string | 用户问题 | 必需 |
| `stream` | boolean | 是否流式返回 | `false` |
| `top_k` | integer | 检索文档数量 | `5` |

#### 响应示例

```json
{
  "answer": "影魔（Shadow Fiend）的技能包括：\n1. 暗影压制...",
  "sources": [
    {
      "content": "暗影压制是影魔的第一个技能...",
      "metadata": {
        "source": "abilities",
        "hero": "Shadow Fiend",
        "ability": "暗影压制"
      },
      "score": 0.92
    }
  ],
  "metadata": {
    "model": "qwen-plus",
    "retrieval_time_ms": 123.45,
    "generation_time_ms": 456.78,
    "total_time_ms": 580.23
  }
}
```

### 2. 数据采集接口

**POST** `/api/ingest`

触发数据采集任务。

#### 请求参数

```json
{
  "full_reload": false
}
```

#### 响应示例

```json
{
  "status": "success",
  "message": "数据采集完成",
  "stats": {
    "total_documents": 8459,
    "duration_seconds": 312.45
  }
}
```

### 3. 健康检查接口

**GET** `/api/health`

检查服务健康状态。

#### 响应示例

```json
{
  "status": "healthy",
  "timestamp": "2026-03-25T15:30:00",
  "version": "1.0.0",
  "components": {
    "vectorstore": "ok",
    "llm": "ok"
  }
}
```

### 4. 统计信息接口

**GET** `/api/stats`

获取数据统计信息。

#### 响应示例

见 [数据统计](#数据统计) 部分。

---

## 🎨 前端界面

项目提供了简洁现代的 Web 交互界面。

### 启动前端

#### 方式 1：直接打开
在浏览器中直接打开 `frontend/index.html`

#### 方式 2：使用 HTTP 服务器
```bash
cd frontend
python -m http.server 8080
```
然后访问 http://localhost:8080

### 功能特性

- 💬 实时问答对话
- 🎨 现代化 UI 设计
- 💡 示例问题快速入口
- ⚡ 异步请求处理
- 📱 响应式布局
- 🌙 深色/浅色主题切换

### 配置后端地址

如需修改后端 API 地址，编辑 `frontend/index.html` 中的 `API_URL` 变量：

```javascript
const API_URL = 'http://localhost:8000/api/ask';
```

---

## 🐳 部署指南

### Docker 部署

#### 1. 构建镜像

```bash
docker build -t dota2-rag:latest .
```

#### 2. 运行容器

```bash
docker run -d \
  --name dota2-rag \
  -p 8000:8000 \
  -e DASHSCOPE_API_KEY=your_api_key_here \
  -v $(pwd)/data:/app/data \
  dota2-rag:latest
```

#### 3. 查看日志

```bash
docker logs -f dota2-rag
```

### 生产环境建议

1. **使用环境变量管理敏感信息**
   ```bash
   docker run -d --env-file .env.prod ...
   ```

2. **持久化数据目录**
   ```bash
   -v /path/to/data:/app/data
   ```

3. **配置反向代理**（Nginx/Caddy）
   ```nginx
   location /api {
       proxy_pass http://localhost:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```

4. **使用进程管理器**（Supervisor/systemd）
   ```ini
   [program:dota2-rag]
   command=uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   directory=/path/to/DOTA2RAG
   autostart=true
   autorestart=true
   ```

---

## 🔧 开发指南

### 本地开发

1. **安装开发依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **启动开发服务器**
   ```bash
   uvicorn src.api.main:app --reload
   ```

3. **代码风格**
   - 遵循 PEP 8 规范
   - 使用类型提示（Type Hints）
   - 编写清晰的文档字符串

### 添加新数据源

1. 在 `src/ingestion/sources/` 创建新的数据源类
2. 实现 `fetch()` 方法返回文档列表
3. 在 `runner.py` 中注册新数据源

示例：
```python
# src/ingestion/sources/my_source.py
from typing import List
from langchain.schema import Document

async def fetch() -> List[Document]:
    """获取自定义数据源"""
    docs = []
    # 实现数据获取逻辑
    return docs
```

### 自定义 RAG 链

编辑 `src/rag/chain.py` 可以自定义：
- 检索策略（相似度阈值、文档数量）
- 提示词模板
- LLM 参数（温度、最大 Token 等）

### 测试

```bash
# 测试数据采集
python -m src.ingestion.runner

# 测试 API 端点
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "测试问题"}'

# 查看健康状态
curl http://localhost:8000/api/health
```

---

## ❓ 常见问题

### 1. API Key 配置问题

**Q**: 提示 "DASHSCOPE_API_KEY 环境变量未设置"

**A**: 确保 `.env` 文件存在并包含有效的 API Key：
```bash
cp .env.example .env
# 编辑 .env 文件填入 API Key
```

### 2. 数据采集失败

**Q**: 数据采集时出现网络错误

**A**: 检查网络连接，确保可以访问 DOTA2 Wiki 和相关数据源。可以设置代理：
```python
# src/ingestion/sources/http_client.py
proxies = {"http": "http://proxy:port", "https": "http://proxy:port"}
```

### 3. 向量数据库为空

**Q**: 查询时提示没有文档

**A**: 首先运行数据采集：
```bash
python -m src.ingestion.runner
```

### 4. 模型不支持

**Q**: 提示模型名称无效

**A**: 确认使用的模型在你的 API 平台中可用，参考 [支持的 API 平台](#支持的-api-平台)。

### 5. 端口占用

**Q**: 启动时提示端口 8000 被占用

**A**: 修改端口号：
```bash
uvicorn src.api.main:app --port 8001
# 或在 .env 中设置 API_PORT=8001
```

### 6. 内存占用过高

**Q**: 运行时内存占用过大

**A**:
- 减少 `top_k` 参数值（默认为 5）
- 调整分块大小（`chunker.py` 中的 `chunk_size`）
- 考虑使用更轻量的嵌入模型

---

## 📊 数据版本

- **当前游戏版本**：7.41
- **最后更新时间**：2026-03-25
- **数据统计**：
  - Wiki 条目：22
  - 英雄数据：127
  - 物品数据：544
  - 技能数据：2706
  - 版本更新：5060

---

## 🤝 贡献指南

欢迎贡献代码和提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 开源协议

本项目采用 MIT 协议开源 - 详见 [LICENSE](LICENSE) 文件

---

## 📮 联系方式

如有问题或建议，欢迎提交 Issue 或 Pull Request。

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给它一个 Star！**

Made with ❤️ for DOTA2 Players

</div>
