## 1. 项目初始化与基础设施

- [x] 1.1 创建项目目录结构（`src/ingestion/sources/`、`src/ingestion/processors/`、`src/vectorstore/`、`src/rag/`、`src/api/routes/`、`config/`、`data/chroma_db/`）
- [x] 1.2 创建 `requirements.txt`，添加核心依赖（langchain、langchain-openai、langchain-chroma、chromadb、fastapi、uvicorn、httpx、python-dotenv、beautifulsoup4）
- [x] 1.3 创建 `config/settings.py`，实现基于环境变量的配置管理（`DASHSCOPE_API_KEY`、`API_BASE_URL`、`EMBEDDING_MODEL`、`CHAT_MODEL`、`CHROMA_PERSIST_DIR`、`API_HOST`、`API_PORT`、`CACHE_TTL`、`LOG_LEVEL`），缺少必需配置时启动失败并报错
- [x] 1.4 创建 `.env.example` 示例配置文件，列出所有环境变量及默认值
- [x] 1.5 创建 `Dockerfile`，支持 Docker 容器化部署

## 2. 数据采集模块（data-ingestion）

- [x] 2.1 实现 `src/ingestion/sources/heroes.py`——从 OpenDota API（`/api/heroes`、`/api/heroStats`）获取英雄数据，包含属性、定位、攻击类型、基础属性和成长值
- [x] 2.2 实现 `src/ingestion/sources/abilities.py`——获取每个英雄的技能详情（技能名称、描述、冷却、魔耗、伤害、神杖/魔晶升级）
- [x] 2.3 实现 `src/ingestion/sources/items.py`——从 OpenDota API（`/api/constants/items`）获取物品数据，包含价格、组件、属性加成、主动/被动技能
- [x] 2.4 实现 `src/ingestion/sources/patches.py`——获取 Patch Notes，解析版本号、发布日期和变更内容
- [x] 2.5 实现 `src/ingestion/sources/wiki.py`——获取游戏机制数据（游戏模式、大厅类型、服务器区域、永久增益等）
- [x] 2.6 实现 API 速率限制处理——OpenDota API 429 响应时指数退避重试（最多 3 次），记录重试日志
- [x] 2.7 实现 `src/ingestion/processors/cleaner.py`——数据清洗（去 HTML 标签、统一空白、标准化数值）和元数据标记（source、category、entity_name、last_updated）
- [x] 2.8 实现 `src/ingestion/processors/chunker.py`——混合分块策略：英雄/物品按实体整块、Patch Notes 按版本+类别分 chunk、Wiki 文章递归字符分割（chunk_size=1000，overlap=200）
- [x] 2.9 实现 `src/ingestion/runner.py`——CLI 入口，支持 `--all`（全量采集）、`--source <name>`（单源采集）

## 3. 向量存储模块（vector-store）

- [x] 3.1 实现 `src/vectorstore/embeddings.py`——封装阿里云 DashScope Embedding 调用，通过 LangChain 的 `OpenAIEmbeddings`（兼容模式），支持批量处理（每批 6 个文档，适配 DashScope 限制）
- [x] 3.2 实现 Embedding 批量分片——每次最多 6 个文档一批发送，自动分批处理大量文档
- [x] 3.3 实现 `src/vectorstore/store.py`——ChromaDB 操作封装：初始化持久化实例（`data/chroma_db/`）、按 Collection 组织文档（heroes、items、patches、wiki）
- [x] 3.4 实现文档 upsert 功能——根据唯一文档 ID 更新已有文档或插入新文档，避免重复
- [x] 3.5 实现相似度搜索接口——支持 top-k 可配置（默认 5）、按元数据过滤（source、category、entity_name）
- [x] 3.6 实现 Collection 管理功能——按 Collection 查询文档数量、清空单个 Collection、列出所有 Collection

## 4. RAG 管线模块（rag-pipeline）

- [x] 4.1 实现 `src/rag/prompts.py`——定义 Dota 2 知识助手的 System Prompt 模板和 RAG Prompt 模板（含系统角色指令、上下文文档、用户问题占位符）
- [x] 4.2 实现 `src/rag/retriever.py`——查询预处理（去空白、语言检测）和中文→英文查询翻译功能（通过 LLM 翻译），支持 `enable_translation` 参数控制
- [x] 4.3 实现多 Collection 联合检索——根据查询意图（关键词匹配）搜索多个 Collection（如英雄问题搜 heroes+patches），合并结果
- [x] 4.4 实现 `src/rag/chain.py`——RAG Chain 核心逻辑：组装上下文 Prompt、调用通义千问（通过 DashScope OpenAI 兼容 API）、处理上下文溢出
- [x] 4.5 实现 LLM API 失败处理——重试最多 3 次，全部失败返回"服务暂时不可用，请稍后重试"
- [x] 4.6 实现来源归因——回答中附带 sources 字段，列出每个贡献文档的类型、实体名称和 Collection
- [x] 4.7 实现响应缓存——基于标准化查询文本+参数的 MD5 哈希缓存响应，TTL 可配置（默认 1 小时），支持缓存命中/过期判断
- [x] 4.8 实现 RAG 参数运行时配置——支持 top_k、temperature、max_tokens、enable_translation 按请求覆盖

## 5. API 服务模块（api-service）

- [x] 5.1 实现 `src/api/main.py`——FastAPI 应用入口，配置 CORS 中间件（默认允许所有来源）、请求日志中间件（记录时间戳、方法、路径、状态码、耗时）
- [x] 5.2 实现 `src/api/schemas.py`——Pydantic 请求/响应模型定义（AskRequest、AskResponse、IngestRequest、HealthResponse、StatsResponse、ErrorResponse）
- [x] 5.3 实现 `POST /api/ask` 路由——接受 question + 可选 RAG 参数，调用 RAG 管线，返回 answer + sources + cached 标记；校验 question 必填、长度 ≤ 1000 字符
- [x] 5.4 实现 `POST /api/ingest` 路由——接受 source 参数（heroes/items/patches/wiki/all），触发对应数据采集任务，返回 HTTP 202；校验 source 合法性
- [x] 5.5 实现 `GET /api/health` 路由——返回服务健康状态（API 状态、ChromaDB 连接、各 Collection 文档数、模型 API 可达性），支持 degraded 状态
- [x] 5.6 实现 `GET /api/stats` 路由——返回各 Collection 统计信息（name、document_count、last_updated）
- [x] 5.7 实现统一错误处理——全局异常处理器，返回 `{"error": "<类型>", "message": "<信息>"}` 格式；针对 500（内部错误）和 429（限流+Retry-After）分别处理

## 6. 集成联调与验证

- [x] 6.1 端到端测试：运行数据采集（`python -m src.ingestion.runner --all`），验证数据成功写入 ChromaDB 各 Collection（heroes: 2833, items: 516, patches: 60, wiki: 22）
- [x] 6.2 端到端测试：启动 API 服务（`uvicorn src.api.main:app`），通过 `/api/ask` 提交中英文 Dota 2 问题，验证返回的回答质量和来源归因
- [x] 6.3 验证缓存功能：连续两次相同查询，确认第二次返回 `cached: true` 且不调用 LLM API
- [ ] 6.4 验证增量更新：先全量采集，再执行 `--incremental`，确认仅处理新数据
- [x] 6.5 验证健康检查和统计接口：调用 `/api/health` 和 `/api/stats`，确认返回正确状态和数据
