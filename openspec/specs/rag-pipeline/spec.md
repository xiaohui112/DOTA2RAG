## ADDED Requirements

### Requirement: 查询理解与预处理

系统必须在检索前对用户查询进行预处理，包括：去除首尾空白、检测查询语言（中文/英文），以及可选地将中文查询翻译为英文以提升检索效果（当数据源主要为英文时）。

#### Scenario: 中文查询翻译

- **WHEN** 用户提交查询"幻影刺客的技能有哪些"
- **THEN** 系统检测为中文，翻译为英文进行检索（"What are Phantom Assassin's abilities"），使用翻译后的查询进行检索，最终以中文生成回答

#### Scenario: 英文查询直通

- **WHEN** 用户提交查询 "What items counter Anti-Mage?"
- **THEN** 系统直接使用原始查询进行检索，无需翻译

### Requirement: 多 Collection 联合检索

系统必须根据查询意图跨多个 ChromaDB Collection 进行搜索，合并不同 Collection 的结果以提供全面的上下文。

#### Scenario: 跨 Collection 英雄查询

- **WHEN** 用户提问"敌法师在最新版本有什么改动"
- **THEN** 系统同时搜索 `heroes` Collection（获取英雄基础信息）和 `patches` Collection（获取最近变更），合并并按相关度排序结果

#### Scenario: 单 Collection 查询

- **WHEN** 用户提问"BKB 多少钱"
- **THEN** 系统主要搜索 `items` Collection 以获取最直接的答案

### Requirement: 上下文组装与 Prompt 构建

系统必须将检索到的文档组装成结构化的 Prompt 提交给 LLM，包括：定义 Dota 2 知识助手角色的系统提示词、检索到的上下文文档和用户的原始问题。

#### Scenario: 标准 Prompt 组装

- **WHEN** 为某个查询检索到 5 个相关文档
- **THEN** 系统构建包含以下内容的 Prompt：(1) 系统角色指令，(2) 检索到的文档作为上下文（附带来源标注），(3) 用户的问题，确保总 token 数不超过 LLM 的上下文窗口限制

#### Scenario: 上下文溢出处理

- **WHEN** 检索到的文档超过 LLM 的上下文限制（DeepSeek V3 为 64K tokens）
- **THEN** 系统必须截断相关度最低的文档（相似度分数最低），使其符合上下文限制，并记录警告日志

### Requirement: 通过 DeepSeek V3 生成回答

系统必须通过硅基流动的 OpenAI 兼容 API 调用 DeepSeek V3 模型，基于组装好的 Prompt 生成回答。

#### Scenario: 成功生成回答

- **WHEN** 将正确构建的 Prompt 提交给 LLM
- **THEN** 系统返回 LLM 生成的回答以及来源引用（哪些文档被用作上下文）

#### Scenario: LLM API 失败处理

- **WHEN** 硅基流动 LLM API 返回错误或超时
- **THEN** 系统必须重试最多 2 次，若全部重试失败则返回用户友好的错误信息："服务暂时不可用，请稍后重试"

### Requirement: 回答中的来源归因

系统必须在生成的回答中包含来源归因，标明哪些数据源（英雄数据、物品数据、补丁版本、Wiki 文章）对回答有贡献。

#### Scenario: 带来源的回答

- **WHEN** LLM 使用来自 3 个不同文档的上下文生成回答
- **THEN** 响应中包含 `sources` 字段，列出每个贡献文档的：文档类型、实体名称和相关度分数

### Requirement: 响应缓存

系统必须缓存查询-响应对以减少重复的 LLM API 调用。缓存键基于标准化后的查询文本，TTL 可配置（默认 1 小时）。

#### Scenario: 缓存命中

- **WHEN** 在 TTL 窗口内提交相同的查询（或标准化后语义相同的查询）
- **THEN** 系统直接返回缓存的响应，不调用 LLM API

#### Scenario: 缓存过期

- **WHEN** 缓存的响应已超过 TTL
- **THEN** 系统将其视为缓存未命中，执行新的检索 + 生成流程

### Requirement: 可配置的 RAG 参数

系统必须支持运行时配置关键 RAG 参数：`top_k`（默认 5）、`temperature`（默认 0.3）、`max_tokens`（默认 2048）和 `enable_translation`（默认 true）。

#### Scenario: 按请求自定义参数

- **WHEN** 提交查询时指定 `top_k=10` 和 `temperature=0.7`
- **THEN** 系统对此次请求使用指定参数，覆盖默认值
