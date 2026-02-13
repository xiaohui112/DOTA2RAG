## MODIFIED Requirements

### Requirement: 从 OpenDota API 获取英雄数据

系统必须从 Dota 2 官方 API 和 OpenDota API 获取所有英雄数据。系统必须首先从 Dota 2 官方 `herolist` API 获取英雄列表（包含中文名、英文名），然后从官方 `herodata` API 获取每个英雄的详细信息（包括技能、属性等）。英雄简称和上线版本必须从外部 JSON 数据文件（`data/hero_nicknames.json` 和 `data/hero_release_versions.json`）加载，而非硬编码在代码中。系统必须确保所有英雄（包括最新上线的英雄如朗戈 hero_id=155）都能被正确获取和处理。

#### Scenario: 成功获取包含完整元数据的英雄数据

- **WHEN** 数据采集管线触发英雄数据采集，且元数据文件存在
- **THEN** 系统从官方 API 获取所有英雄的基础信息和详细信息，从 JSON 文件加载简称和版本映射，输出每个英雄的完整数据（包含 `name_loc`、`name_english_loc`、`nicknames`、`release_version`、`abilities` 等字段）

#### Scenario: 新英雄缺少元数据时的处理

- **WHEN** 系统获取到新英雄（如朗戈 hero_id=155），但 JSON 文件中没有该英雄的简称或版本映射
- **THEN** 系统正常返回该英雄的数据，`nicknames` 字段为空列表，`release_version` 字段为 None，不抛出异常，记录 info 日志说明元数据缺失

#### Scenario: 元数据文件缺失时的英雄数据采集

- **WHEN** 数据采集管线触发英雄数据采集，但 `data/hero_nicknames.json` 或 `data/hero_release_versions.json` 文件不存在
- **THEN** 系统从官方 API 正常获取所有英雄数据，所有英雄的 `nicknames` 为空列表，`release_version` 为 None，记录 warning 日志说明元数据文件缺失，采集流程继续执行

#### Scenario: 确保最新英雄能被正确获取

- **WHEN** 系统调用 `fetch_heroes()` 获取英雄数据，包括最新上线的英雄（如朗戈 hero_id=155）
- **THEN** 系统从官方 `herolist` API 获取到包含该英雄的完整列表，从 `herodata` API 获取该英雄的详细信息（包括所有技能），返回的英雄数据包含完整的属性、技能等信息，即使元数据文件中没有该英雄的简称或版本映射
