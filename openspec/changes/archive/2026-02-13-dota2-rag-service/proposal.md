## Why

Dota 2 拥有海量的游戏数据（150+ 英雄、200+ 物品、技能机制、版本更新日志、对战策略等），玩家和内容创作者在查询特定信息时往往需要在多个 Wiki、论坛、补丁说明中来回翻找，效率极低。构建一个基于 RAG（Retrieval-Augmented Generation）的智能问答服务，可以让用户通过自然语言直接获取精准的 Dota 2 知识，极大提升信息获取体验。

## What Changes

- 新增 Dota 2 游戏数据采集与处理管线，支持从 OpenDota API、Dota 2 Wiki、Patch Notes 等数据源获取结构化和非结构化数据
- 新增文本向量化与向量数据库存储能力，将处理后的 Dota 2 知识转化为可检索的 Embedding
- 新增 RAG 查询管线，实现检索增强生成，结合向量检索结果与 LLM 生成高质量回答
- 新增 REST API 服务，对外暴露问答接口，支持用户以自然语言提问 Dota 2 相关问题

## Capabilities

### New Capabilities

- `data-ingestion`: 负责从多种数据源（OpenDota API、Dota 2 Wiki、Patch Notes）采集、清洗、分块处理 Dota 2 游戏数据，输出标准化的文档块（chunks）
- `vector-store`: 将文档块进行 Embedding 向量化，存入向量数据库（如 ChromaDB/FAISS），支持相似度检索
- `rag-pipeline`: RAG 核心查询管线——接收用户问题，从向量库中检索相关上下文，组装 Prompt 并调用 LLM 生成回答
- `api-service`: 提供 RESTful API 接口，暴露问答、数据刷新等端点，处理请求/响应和错误

### Modified Capabilities

（无已有 capability 需要修改）

## Impact

- **新增依赖**：Python 生态（LangChain）、向量数据库（ChromaDB）、Embedding 模型（BAAI/bge-m3 via 硅基流动免费 API）、LLM（DeepSeek V3 via 硅基流动免费 API）
- **外部 API**：OpenDota API（公开，有速率限制）、Dota 2 Wiki 爬取
- **基础设施**：需要向量数据库持久化存储、API 服务部署（可 Docker 化）
- **代码结构**：全新项目，在项目根目录下新建 `src/` 目录组织各模块代码
- **安全与配置**：需管理硅基流动 API Key 等敏感配置（通过环境变量 / .env 文件）
