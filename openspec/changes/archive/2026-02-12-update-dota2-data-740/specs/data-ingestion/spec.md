## MODIFIED Requirements

### Requirement: 获取版本更新日志（Patch Notes）

系统必须获取 Dota 2 版本更新日志的完整变更内容。系统必须首先从 OpenDota API（`/api/constants/patch`）获取版本列表（版本号和日期），然后使用 `patch-notes-scraper` 模块从 Dota 2 官方网站抓取每个版本的详细变更内容（通用改动、英雄改动、物品改动）。如果官网抓取失败，系统必须降级为仅保存版本号和日期信息。

#### Scenario: 成功获取包含完整变更内容的补丁数据

- **WHEN** 数据采集管线触发补丁数据采集，且 Dota 2 官网可访问
- **THEN** 系统输出每个版本的文档，包含版本号、日期和按类别组织的完整变更内容（通用改动、英雄改动、物品改动）

#### Scenario: 官网不可访问时降级

- **WHEN** 数据采集管线触发补丁数据采集，但 Dota 2 官网抓取全部失败
- **THEN** 系统降级为仅保存从 OpenDota API 获取的版本号和日期，记录警告日志说明变更内容缺失

#### Scenario: 增量更新补丁说明

- **WHEN** 采集管线检测到本地 `version_meta.json` 中不存在的新版本补丁
- **THEN** 系统必须仅获取和处理新版本的 Patch Notes，不修改已有数据

### Requirement: 按数据类型分块

系统必须根据数据类型采用不同的分块策略：
- 英雄/物品数据：每个实体作为一个独立文档（不再细分）
- 补丁说明：每个版本按类别拆分为多个 chunk——"通用改动"、"英雄改动"、"物品改动"各一个 chunk。如果英雄改动部分超过 1500 字符，必须进一步按英雄名拆分为独立 chunk
- Wiki 文章：使用递归字符分割，chunk_size=1000，overlap=200

#### Scenario: 补丁文档按类别分块

- **WHEN** 处理 7.40 版本的 Patch Notes，包含通用改动、15 个英雄改动和 10 个物品改动
- **THEN** 系统至少输出 3 个 chunk：通用改动 chunk、英雄改动 chunk、物品改动 chunk，每个 chunk 的元数据包含 `patch_version: "7.40"` 和 `change_category`（general/hero/item）

#### Scenario: 大版本英雄改动进一步拆分

- **WHEN** 处理某大版本 Patch Notes，其英雄改动部分超过 1500 字符
- **THEN** 系统将英雄改动拆分为按英雄名分组的独立 chunk，每个 chunk 包含元数据 `hero_name` 和 `patch_version`

#### Scenario: 英雄文档分块

- **WHEN** 处理"敌法师"的英雄数据
- **THEN** 系统输出一个包含敌法师所有属性、技能和天赋树信息的完整文档

#### Scenario: Wiki 文章分块

- **WHEN** 处理一篇超过 1000 字符的 Wiki 文章
- **THEN** 系统将其拆分为约 1000 字符的重叠块（overlap=200），每个块继承父文档的元数据

### Requirement: 数据采集 CLI 入口

系统必须提供 CLI 入口（`python -m src.ingestion.runner`），支持：全量采集所有数据源（`--all`）、单数据源采集（`--source heroes`）、增量更新模式（`--incremental`，仅采集新数据）和数据检查模式（`--check`，仅检查是否有更新而不执行采集）。

#### Scenario: 全量采集

- **WHEN** 用户执行 `python -m src.ingestion.runner --all`
- **THEN** 系统从所有数据源（英雄、物品、技能、补丁、Wiki）获取数据，处理分块后输出到向量库，并更新 `version_meta.json`

#### Scenario: 单数据源采集

- **WHEN** 用户执行 `python -m src.ingestion.runner --source heroes`
- **THEN** 系统仅获取和处理英雄数据，不影响其他数据，并仅更新 `version_meta.json` 中 heroes 相关字段

#### Scenario: 增量更新模式

- **WHEN** 用户执行 `python -m src.ingestion.runner --incremental`
- **THEN** 系统读取 `version_meta.json`，比对远程数据源，仅采集有变化的数据源（新补丁版本或数量变化的英雄/物品），跳过无变化的数据源

#### Scenario: 数据检查模式

- **WHEN** 用户执行 `python -m src.ingestion.runner --check`
- **THEN** 系统读取 `version_meta.json` 并查询远程数据源，输出各数据源的更新状态摘要（如"heroes: 124 → 126, 需要更新"），但不执行任何数据采集或写入操作

## ADDED Requirements

### Requirement: 采集完成后更新版本元信息

每次数据采集完成后，系统必须更新 `data/version_meta.json` 中对应数据源的元信息。更新内容包括：文档数量（count）、更新时间（updated_at）、以及全局的最后更新时间（last_updated）和游戏版本号（game_version，取最新补丁版本号）。

#### Scenario: 全量采集后更新所有元信息

- **WHEN** 全量采集完成（`--all` 模式），共采集 126 个英雄、208 个物品、45 个补丁
- **THEN** `version_meta.json` 中 heroes.count 为 126、items.count 为 208、patches.count 为 45，所有 updated_at 字段更新为当前时间

#### Scenario: 单数据源采集后仅更新对应元信息

- **WHEN** 仅采集英雄数据后（`--source heroes`）
- **THEN** 仅更新 `version_meta.json` 中 heroes 的 count 和 updated_at 字段，其他数据源的元信息保持不变
