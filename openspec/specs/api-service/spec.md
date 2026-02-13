## ADDED Requirements

### Requirement: POST /api/ask 问答接口

系统必须提供 `POST /api/ask` 接口，接受包含 `question` 字段（字符串，必填）和可选 RAG 参数（`top_k`、`temperature`、`max_tokens`）的 JSON 请求体，返回生成的回答及来源归因。

#### Scenario: 成功回答问题

- **WHEN** 客户端发送 `POST /api/ask`，请求体为 `{"question": "Pudge 的钩子距离是多少"}`
- **THEN** 系统返回 HTTP 200，JSON 响应包含 `answer`（字符串）、`sources`（来源对象数组）和 `cached`（布尔值，表示是否来自缓存）

#### Scenario: 缺少 question 字段

- **WHEN** 客户端发送 `POST /api/ask`，请求体为空或缺少 `question` 字段
- **THEN** 系统返回 HTTP 422 及校验错误信息

#### Scenario: 问题过长

- **WHEN** 客户端发送的问题超过 1000 个字符
- **THEN** 系统返回 HTTP 400，错误信息为"问题长度不能超过 1000 个字符"

### Requirement: POST /api/ingest 数据采集接口

系统必须提供 `POST /api/ingest` 接口，触发数据采集任务，接受可选的 `source` 参数指定采集的数据源（heroes、items、patches、wiki 或 all）。

#### Scenario: 触发全量采集

- **WHEN** 客户端发送 `POST /api/ingest`，请求体为 `{"source": "all"}`
- **THEN** 系统触发所有数据源的采集任务，返回 HTTP 202 及任务状态响应

#### Scenario: 触发单数据源采集

- **WHEN** 客户端发送 `POST /api/ingest`，请求体为 `{"source": "heroes"}`
- **THEN** 系统仅触发英雄数据的采集

#### Scenario: 无效的 source 参数

- **WHEN** 客户端发送 `POST /api/ingest`，请求体为 `{"source": "invalid"}`
- **THEN** 系统返回 HTTP 400，错误信息中列出有效的 source 选项

### Requirement: GET /api/health 健康检查接口

系统必须提供 `GET /api/health` 接口，返回服务健康状态，包括：API 状态、ChromaDB 连接状态、各 Collection 文档数量和模型 API 可达性。

#### Scenario: 服务健康

- **WHEN** 所有组件运行正常
- **THEN** 系统返回 HTTP 200，响应体为 `{"status": "healthy", "chroma": "connected", "collections": {"heroes": 125, "items": 208, ...}, "model_api": "reachable"}`

#### Scenario: 服务降级

- **WHEN** 硅基流动 API 不可达但 ChromaDB 正常
- **THEN** 系统返回 HTTP 200，响应体为 `{"status": "degraded", "chroma": "connected", "model_api": "unreachable"}`

### Requirement: GET /api/stats 统计接口

系统必须提供 `GET /api/stats` 接口，返回各 Collection 的统计信息，包括文档数量、最后采集时间和数据新鲜度。

#### Scenario: 获取统计信息

- **WHEN** 客户端发送 `GET /api/stats`
- **THEN** 系统返回 HTTP 200，包含各 Collection 的统计数据：`name`、`document_count`、`last_updated`

### Requirement: CORS 跨域支持

系统必须启用 CORS（跨域资源共享），支持可配置的允许来源，开发环境默认为 `*`（允许所有来源）。

#### Scenario: 跨域请求

- **WHEN** 来自不同域名的浏览器客户端发送请求
- **THEN** 系统在响应中包含适当的 CORS 头（`Access-Control-Allow-Origin` 等）

### Requirement: 统一错误处理与响应格式

系统必须对所有错误返回统一的 JSON 错误响应，格式为 `{"error": "<错误类型>", "message": "<可读错误信息>"}`，使用合适的 HTTP 状态码。

#### Scenario: 服务器内部错误

- **WHEN** 请求处理过程中发生未预期的异常
- **THEN** 系统返回 HTTP 500，响应体为 `{"error": "internal_error", "message": "服务器内部错误，请稍后重试"}`，并记录完整的堆栈跟踪日志

#### Scenario: 限流响应

- **WHEN** 上游模型 API 被限流
- **THEN** 系统返回 HTTP 429，响应体为 `{"error": "rate_limited", "message": "请求过于频繁，请稍后重试"}`，并包含 `Retry-After` 响应头

### Requirement: 请求日志记录

系统必须记录所有传入的 API 请求，包括：时间戳、请求方法、路径、响应状态码和响应耗时（毫秒）。

#### Scenario: 请求审计追踪

- **WHEN** 处理任何 API 请求
- **THEN** 写入一条结构化日志，包含请求元数据和耗时信息

### Requirement: 通过环境变量配置

系统必须从环境变量读取所有配置（支持 `.env` 文件），包括：`SILICONFLOW_API_KEY`、`CHROMA_PERSIST_DIR`（默认 `data/chroma_db`）、`API_HOST`（默认 `0.0.0.0`）、`API_PORT`（默认 `8000`）、`CACHE_TTL`（默认 `3600`）、`LOG_LEVEL`（默认 `INFO`）。

#### Scenario: 自定义配置

- **WHEN** 设置环境变量 `API_PORT=9000`
- **THEN** FastAPI 服务在 9000 端口启动

#### Scenario: 缺少必需配置

- **WHEN** 未设置 `SILICONFLOW_API_KEY` 环境变量
- **THEN** 应用必须启动失败，并显示明确的错误信息："SILICONFLOW_API_KEY 环境变量未设置"
