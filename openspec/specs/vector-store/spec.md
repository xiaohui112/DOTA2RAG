## ADDED Requirements

### Requirement: 使用 bge-m3 通过硅基流动 API 进行文档向量化

系统必须使用 BAAI/bge-m3 模型，通过硅基流动的 OpenAI 兼容 API 端点（`https://api.siliconflow.cn/v1`），将文档块转换为向量 Embedding。

#### Scenario: 成功生成 Embedding

- **WHEN** 提交一批文档块进行向量化
- **THEN** 系统调用硅基流动 Embedding API，为每个块返回 1024 维向量

#### Scenario: API 失败与重试

- **WHEN** 硅基流动 API 不可用或返回错误
- **THEN** 系统必须以指数退避策略重试最多 3 次，并记录详细错误信息

#### Scenario: 批量 Embedding 提升效率

- **WHEN** 超过 10 个文档需要向量化
- **THEN** 系统必须将文档分批处理，每次 API 调用最多 64 个文档，以减少请求开销

### Requirement: 将 Embedding 存入 ChromaDB

系统必须将所有文档 Embedding 及其元数据持久化到 ChromaDB 实例（SQLite 后端），存储路径为 `data/chroma_db/`。

#### Scenario: 成功存储

- **WHEN** 一批文档的 Embedding 生成完成
- **THEN** 系统将每个 Embedding 连同文档文本内容和元数据（source、category、entity_name、last_updated）存入 ChromaDB

#### Scenario: 重启后数据持久化

- **WHEN** 应用程序重启
- **THEN** 之前存储的 Embedding 和文档必须可用，无需重新采集

### Requirement: 相似度检索

系统必须支持相似度搜索，返回与给定查询文本最相关的 top-k 个文档，k 值可配置（默认 k=5）。

#### Scenario: 基本相似度搜索

- **WHEN** 提交查询"敌法师的技能有哪些"
- **THEN** 系统返回最多 5 个语义最相似的文档，按相关度分数排序

#### Scenario: 自定义 top-k 值

- **WHEN** 请求相似度搜索并指定 k=10
- **THEN** 系统返回最多 10 个最相关的文档

### Requirement: 基于元数据的检索过滤

系统必须支持按元数据字段过滤搜索结果，包括：`source`、`category` 和 `entity_name`。

#### Scenario: 按类别过滤

- **WHEN** 执行搜索并指定过滤条件 `category=hero`
- **THEN** 仅对 `category=hero` 的文档进行相似度搜索

#### Scenario: 组合过滤与相似度搜索

- **WHEN** 搜索"伤害调整"并指定过滤条件 `source=patch`
- **THEN** 仅在补丁说明文档中搜索，返回最相关的补丁变更结果

### Requirement: 增量 Upsert 支持

系统必须支持文档的 upsert 操作——根据唯一文档 ID 更新已有文档或插入新文档——无需全量重建索引。

#### Scenario: 更新已有英雄文档

- **WHEN** 重新采集"敌法师"英雄数据且属性已更新
- **THEN** 系统在 ChromaDB 中更新敌法师对应文档（相同 ID），替换为新的 Embedding 和内容，不产生重复条目

#### Scenario: 新增补丁说明

- **WHEN** 采集新版本补丁（如 7.38）
- **THEN** 系统插入新版本文档，不修改已有的补丁数据

### Requirement: Collection 管理

系统必须将文档组织到 ChromaDB 的逻辑 Collection 中：`heroes`、`items`、`patches`、`wiki`，支持按 Collection 进行操作（清空、计数、列表）。

#### Scenario: 查询 Collection 文档数量

- **WHEN** 用户请求查询 `heroes` Collection 的文档数量
- **THEN** 系统返回该 Collection 中存储的文档总数

#### Scenario: 清空单个 Collection

- **WHEN** 用户请求清空 `patches` Collection
- **THEN** 仅删除补丁文档，其他 Collection 保持不变
