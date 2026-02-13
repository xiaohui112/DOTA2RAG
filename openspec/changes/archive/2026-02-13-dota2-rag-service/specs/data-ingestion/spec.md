## ADDED Requirements

### Requirement: 从 OpenDota API 获取英雄数据

系统必须从 OpenDota API（`/api/heroes` 和 `/api/heroStats`）获取所有 Dota 2 英雄数据，包括英雄名称、属性、定位、攻击类型、基础属性值和每级成长值。

#### Scenario: 成功获取英雄数据

- **WHEN** 数据采集管线触发英雄数据采集
- **THEN** 系统获取全部 120+ 英雄的完整属性数据，每个英雄输出为一个独立文档

#### Scenario: OpenDota API 速率限制处理

- **WHEN** OpenDota API 返回 429（被限流）响应
- **THEN** 系统必须等待后以指数退避策略重试（最多 3 次），并记录每次重试日志

### Requirement: 获取英雄技能描述

系统必须获取每个英雄的详细技能信息，包括技能名称、描述、冷却时间、魔法消耗、伤害数值以及特殊机制（如阿哈利姆神杖/魔晶升级效果）。

#### Scenario: 包含神杖升级的技能

- **WHEN** 某英雄拥有阿哈利姆神杖或魔晶升级效果
- **THEN** 系统必须将升级描述作为该英雄技能文档的一部分

### Requirement: 从 OpenDota API 获取物品数据

系统必须从 OpenDota API（`/api/constants/items`）获取所有 Dota 2 物品数据，包括物品名称、价格、合成组件、属性加成、主动/被动技能以及合成配方。

#### Scenario: 成功获取物品数据

- **WHEN** 数据采集管线触发物品数据采集
- **THEN** 系统获取全部 200+ 物品的完整属性数据，每个物品输出为一个独立文档

### Requirement: 获取版本更新日志（Patch Notes）

系统必须获取 Dota 2 版本更新日志，解析版本号、发布日期以及每个补丁中所有英雄/物品/通用变更内容。

#### Scenario: 解析结构化补丁说明

- **WHEN** 获取特定版本的补丁说明
- **THEN** 系统输出每个版本一个文档，变更内容按类别（通用、英雄、物品）组织

#### Scenario: 增量更新补丁说明

- **WHEN** 采集管线检测到本地数据中不存在的新版本补丁
- **THEN** 系统必须仅获取和处理新补丁说明，不修改已有数据

### Requirement: 爬取 Dota 2 Wiki 文章

系统必须爬取 Dota 2 Wiki 中的关键攻略和机制文章，包括游戏机制（护甲、伤害类型、状态效果）、分路定位和玩法指南。

#### Scenario: Wiki 文章内容提取

- **WHEN** 数据采集管线触发 Wiki 数据采集
- **THEN** 系统提取文章正文内容，去除 HTML/格式标记，保留段落结构

### Requirement: 数据清洗与标准化

系统必须对所有采集的数据进行清洗和标准化处理，包括：去除 HTML 标签、统一空白字符、转换数值为一致格式，并添加元数据标签（source、category、entity_name、last_updated）。

#### Scenario: 元数据标记

- **WHEN** 任何文档经过清洗管线处理
- **THEN** 每个输出文档必须包含以下元数据字段：`source`（api/wiki/patch）、`category`（hero/item/patch/mechanic）、`entity_name` 以及 `last_updated` 时间戳

### Requirement: 按数据类型分块

系统必须根据数据类型采用不同的分块策略：
- 英雄/物品数据：每个实体作为一个独立文档（不再细分）
- 补丁说明：每个版本为一个文档，按类别章节拆分为 chunk
- Wiki 文章：使用递归字符分割，chunk_size=1000，overlap=200

#### Scenario: 英雄文档分块

- **WHEN** 处理"敌法师"的英雄数据
- **THEN** 系统输出一个包含敌法师所有属性、技能和天赋树信息的完整文档

#### Scenario: Wiki 文章分块

- **WHEN** 处理一篇超过 1000 字符的 Wiki 文章
- **THEN** 系统将其拆分为约 1000 字符的重叠块（overlap=200），每个块继承父文档的元数据

### Requirement: 数据采集 CLI 入口

系统必须提供 CLI 入口（`python -m src.ingestion.runner`），支持：全量采集所有数据源、单数据源采集（如 `--source heroes`）和增量更新模式（`--incremental`）。

#### Scenario: 全量采集

- **WHEN** 用户执行 `python -m src.ingestion.runner --all`
- **THEN** 系统从所有数据源（英雄、物品、补丁、Wiki）获取数据，处理分块后输出到向量库

#### Scenario: 单数据源采集

- **WHEN** 用户执行 `python -m src.ingestion.runner --source heroes`
- **THEN** 系统仅获取和处理英雄数据，不影响其他数据
