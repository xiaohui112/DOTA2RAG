## Context

本项目是一个全新的 Dota 2 RAG 智能问答服务。当前没有任何已有代码或基础设施。目标是从零构建一个完整的 RAG 系统，涵盖数据采集、向量化存储、检索增强生成和 API 服务四大模块。

Dota 2 数据具有以下特点：
- **结构化数据**：英雄属性、物品数据、技能数值等，来自 OpenDota API
- **非结构化数据**：版本更新日志（Patch Notes）、Wiki 文章、攻略文章等
- **频繁更新**：每个大版本补丁会大量调整英雄/物品数据，需支持增量更新
- **多语言**：数据源以英文为主，但用户提问可能使用中文

主要约束：
- OpenDota API 有速率限制（每分钟 60 次）
- 使用国内免费模型 API（硅基流动），需注意免费额度限制和速率控制
- 初版以单机部署为目标，后续可扩展

## Goals / Non-Goals

**Goals:**

- 构建端到端的 RAG 管线，支持用户用自然语言查询 Dota 2 知识
- 覆盖核心数据源：英雄、物品、技能、Patch Notes
- 提供稳定的 REST API 接口，响应时间 < 5s
- 支持数据增量更新，无需全量重建索引
- 支持中英文混合查询

**Non-Goals:**

- 不做实时比赛数据分析（如 live match tracking）
- 不做用户系统和认证（初版为开放 API）
- 不做前端 UI（仅提供 API，前端由消费方自行构建）
- 不做多租户隔离
- 不做模型微调（使用通用 LLM + Prompt Engineering）

## Decisions

### 1. 编排框架：LangChain

**选择**：使用 LangChain 作为 RAG 编排框架

**理由**：
- LangChain 生态成熟，社区活跃，文档丰富
- 内置 Document Loader、Text Splitter、Vector Store、Retriever、Chain 等完整抽象
- 对主流 LLM 和向量数据库都有开箱即用的集成
- 相比 LlamaIndex 更灵活，适合自定义管线

**替代方案**：
- LlamaIndex：更偏向索引和检索，但自定义管线灵活度稍低
- 纯手写：完全自定义但开发成本高，不适合初版快速验证

### 2. 向量数据库：ChromaDB

**选择**：使用 ChromaDB 作为向量数据库

**理由**：
- 轻量级，可内嵌运行，无需独立部署数据库服务
- 支持持久化存储（SQLite 后端）
- Python-native API，与 LangChain 集成良好
- 适合单机部署的初版场景

**替代方案**：
- FAISS：Meta 开源，检索性能极高，但不支持持久化元数据、无内置过滤
- Milvus/Qdrant：功能更强但需独立部署，初版过重
- Pinecone：全托管但依赖云服务，增加外部依赖和成本

### 3. Embedding 模型：BAAI/bge-m3（通过硅基流动免费 API）

**选择**：使用 `BAAI/bge-m3` Embedding 模型，通过硅基流动（SiliconFlow）免费 API 调用

**理由**：
- 完全免费，硅基流动提供 bge-m3 的免费推理 API
- bge-m3 是北京智源研究院（BAAI）开源的多语言 Embedding 模型，中英文效果均优秀
- 支持 8192 token 长文本，适合较长的游戏文档分块
- 硅基流动 API 兼容 OpenAI 格式，LangChain 可通过 `OpenAIEmbeddings` 直接对接（修改 base_url）
- 维度 1024，质量与 OpenAI text-embedding-3-small 相当

**替代方案**：
- OpenAI text-embedding-3-small：质量好但收费（$0.02/1M tokens）
- 通义千问 Embedding（text-embedding-v3）：阿里云 DashScope 有免费额度，但额度有限
- 本地部署 bge-m3：免费无限制但需 GPU，初版不考虑

### 4. LLM：DeepSeek V3（通过硅基流动免费 API）

**选择**：使用 `DeepSeek V3` 作为生成模型，通过硅基流动（SiliconFlow）免费 API 调用

**理由**：
- 完全免费，硅基流动提供 DeepSeek V3 的免费推理额度
- DeepSeek V3 中文能力极强，非常适合中文用户场景
- 支持 64K 上下文窗口，足够容纳检索结果 + Prompt
- API 兼容 OpenAI 格式（base_url 改为 `https://api.siliconflow.cn/v1`），LangChain 无缝对接
- 推理质量接近 GPT-4o 水平，远超 GPT-4o-mini

**替代方案**：
- DeepSeek 官方 API：也很便宜（¥1/1M tokens），但不如硅基流动免费额度划算
- 通义千问（Qwen-Max）：阿里云 DashScope 有免费额度，质量也不错，可作为备选
- 智谱 GLM-4-Flash：智谱清言免费版，质量稍逊但也可用
- OpenAI GPT-4o-mini：质量好但收费，且需科学上网

### 5. API 框架：FastAPI

**选择**：使用 FastAPI 构建 REST API

**理由**：
- 异步支持好，性能优秀
- 自动生成 OpenAPI 文档
- 类型提示友好，开发体验好
- Python 生态中最主流的 API 框架之一

**替代方案**：
- Flask：更简单但不支持异步，不适合 I/O 密集的 RAG 场景
- Django REST：太重，不适合纯 API 服务

### 6. 数据分块策略：混合分块

**选择**：根据数据类型采用不同分块策略

- **结构化数据**（英雄/物品）：每个英雄/物品作为一个独立文档，包含所有属性和技能描述
- **Patch Notes**：按版本号分段，每个版本为一个文档，内部按英雄/物品变更细分 chunk
- **Wiki 文章**：使用 RecursiveCharacterTextSplitter，chunk_size=1000，overlap=200

**理由**：
- 结构化数据天然有边界，按实体分块保持语义完整性
- Patch Notes 按版本分割，便于版本过滤检索
- Wiki 长文使用重叠分块确保上下文连续性

### 7. 项目结构

```
DOTA2RAG/
├── src/
│   ├── ingestion/          # 数据采集模块
│   │   ├── sources/        # 各数据源采集器
│   │   ├── processors/     # 数据清洗和分块
│   │   └── runner.py       # 采集管线入口
│   ├── vectorstore/        # 向量存储模块
│   │   ├── embeddings.py   # Embedding 封装
│   │   └── store.py        # ChromaDB 操作封装
│   ├── rag/                # RAG 管线模块
│   │   ├── retriever.py    # 检索器
│   │   ├── chain.py        # LangChain RAG Chain
│   │   └── prompts.py      # Prompt 模板
│   └── api/                # API 服务模块
│       ├── main.py         # FastAPI 应用入口
│       ├── routes/         # 路由定义
│       └── schemas.py      # 请求/响应模型
├── data/                   # 本地数据存储
│   └── chroma_db/          # ChromaDB 持久化目录
├── config/
│   └── settings.py         # 配置管理
├── requirements.txt
├── Dockerfile
└── .env.example
```

## Risks / Trade-offs

- **[硅基流动免费额度]** → 免费 API 有调用次数/token 限制，高频使用可能耗尽额度。**缓解**：设置响应缓存（相同问题短时间内复用结果），控制检索返回的 chunk 数量（top_k=5）；预留切换到 DeepSeek 官方 API 或通义千问的能力。

- **[数据新鲜度]** → Dota 2 版本更新频繁，数据可能滞后。**缓解**：设计增量更新机制，支持手动或定时触发数据刷新。

- **[中文查询质量]** → 数据源以英文为主，但 bge-m3 和 DeepSeek V3 均有优秀的中英文能力。**缓解**：在 RAG 管线中可选加入查询翻译步骤（中文 → 英文），检索后再用中文生成回答。bge-m3 的多语言能力也可直接处理中文查询。

- **[模型服务稳定性]** → 依赖硅基流动第三方平台，若平台不可用则服务中断。**缓解**：抽象 Embedding 和 LLM 接口，支持一键切换到 DeepSeek 官方 API、阿里云 DashScope（通义千问）等备选平台。

- **[ChromaDB 扩展性]** → ChromaDB 适合单机场景，数据量大时性能可能下降。**缓解**：初版数据量可控（~10K documents），后续如需扩展可迁移至 Milvus/Qdrant。

## Open Questions

- 是否需要支持流式响应（SSE）以提升用户体验？
- Patch Notes 历史数据回溯到哪个版本（全部 vs 最近 N 个版本）？
- 是否集成 Dota 2 社区攻略内容（如 Dotabuff 策略文章）？
