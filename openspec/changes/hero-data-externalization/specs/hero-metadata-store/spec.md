## ADDED Requirements

### Requirement: 英雄元数据外部化存储

系统必须从外部 JSON 文件加载英雄元数据（简称映射和上线版本映射），而非硬编码在代码中。元数据文件必须存储在 `data/` 目录下，格式为 JSON，支持懒加载和缓存机制。

#### Scenario: 从 JSON 文件加载英雄简称映射

- **WHEN** 系统首次调用 `_get_hero_nicknames(hero_name)` 函数
- **THEN** 系统从 `data/hero_nicknames.json` 加载映射数据，缓存到模块级变量，返回该英雄的简称列表；如果文件不存在或解析失败，返回空列表并记录 warning 日志

#### Scenario: 从 JSON 文件加载英雄上线版本映射

- **WHEN** 系统首次调用 `_find_hero_release_version(hero_name)` 函数
- **THEN** 系统从 `data/hero_release_versions.json` 加载映射数据，缓存到模块级变量，返回该英雄的上线版本号；如果文件不存在或解析失败，返回 None 并记录 warning 日志

#### Scenario: 元数据文件缺失时的容错处理

- **WHEN** `data/hero_nicknames.json` 或 `data/hero_release_versions.json` 文件不存在
- **THEN** 系统不抛出异常，返回空映射（空列表或 None），记录 warning 日志说明文件缺失，英雄数据采集流程继续正常执行

#### Scenario: JSON 文件格式错误时的容错处理

- **WHEN** JSON 文件存在但格式错误（如语法错误、类型不匹配）
- **THEN** 系统捕获 JSON 解析异常，返回空映射，记录 error 日志包含具体错误信息，英雄数据采集流程继续正常执行

### Requirement: 英雄元数据文件格式

英雄元数据文件必须遵循以下 JSON 格式规范：

- `data/hero_nicknames.json`: Key 为英雄内部名称（`npc_dota_hero_xxx`），Value 为简称字符串数组
- `data/hero_release_versions.json`: Key 为英雄内部名称（`npc_dota_hero_xxx`），Value 为版本号字符串（如 "6.00"、"7.38"）

#### Scenario: 英雄简称文件格式验证

- **WHEN** 系统加载 `data/hero_nicknames.json` 文件
- **THEN** 系统验证文件格式：每个 key 必须是字符串，每个 value 必须是字符串数组；格式正确时正常加载，格式错误时记录 error 并返回空映射

#### Scenario: 英雄版本文件格式验证

- **WHEN** 系统加载 `data/hero_release_versions.json` 文件
- **THEN** 系统验证文件格式：每个 key 必须是字符串，每个 value 必须是字符串；格式正确时正常加载，格式错误时记录 error 并返回空映射
