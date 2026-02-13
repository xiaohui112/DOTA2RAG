## ADDED Requirements

### Requirement: 持久化存储数据版本元信息

系统必须在 `data/version_meta.json` 文件中持久化存储数据版本追踪元信息。文件必须包含：全局最后更新时间、当前游戏版本号、以及每个数据源（heroes、items、abilities、patches、wiki）的文档数量、最后更新时间和特定版本标识（如补丁数据的最新版本号）。

#### Scenario: 首次采集后创建版本元信息文件

- **WHEN** 系统首次执行数据采集且 `data/version_meta.json` 不存在
- **THEN** 系统必须创建该文件，写入本次采集的所有元信息，包括 ISO 8601 格式的时间戳

#### Scenario: 后续采集更新版本元信息

- **WHEN** 系统执行数据采集后（包括单数据源和全量采集）
- **THEN** 系统必须更新 `version_meta.json` 中对应数据源的 `count` 和 `updated_at` 字段，以及全局的 `last_updated` 字段

#### Scenario: 版本元信息文件损坏时的恢复

- **WHEN** `version_meta.json` 文件内容损坏（JSON 解析失败）
- **THEN** 系统必须记录警告日志，丢弃损坏数据并重新创建空的元信息文件，不影响采集流程

### Requirement: 读取版本元信息

系统必须提供读取 `data/version_meta.json` 内容的函数。如果文件不存在，必须返回表示"从未采集"的默认空结构。

#### Scenario: 读取已存在的版本元信息

- **WHEN** 调用读取函数且 `data/version_meta.json` 存在并包含有效 JSON
- **THEN** 函数返回解析后的字典，包含 `last_updated`、`game_version` 和 `sources` 字段

#### Scenario: 读取不存在的版本元信息

- **WHEN** 调用读取函数且 `data/version_meta.json` 不存在
- **THEN** 函数返回默认结构 `{"last_updated": null, "game_version": null, "sources": {}}`

### Requirement: 数据新鲜度检查

系统必须提供检查数据是否需要更新的能力。通过比对本地版本元信息与远程数据源（OpenDota API）返回的数据，判断各数据源是否有新内容。

#### Scenario: 检测到新补丁版本

- **WHEN** 本地 `version_meta.json` 中 `patches.latest_patch` 为 "7.39"，但 OpenDota API `/api/constants/patch` 返回的列表中包含 "7.40"
- **THEN** 系统报告 patches 数据需要更新，并列出缺失的版本号列表

#### Scenario: 检测到新英雄

- **WHEN** 本地 `version_meta.json` 中 `heroes.count` 为 124，但 OpenDota API `/api/heroes` 返回 126 个英雄
- **THEN** 系统报告 heroes 数据需要更新，并指出英雄数量从 124 增加到 126

#### Scenario: 所有数据均为最新

- **WHEN** 本地版本元信息中各数据源的数量和版本号与远程 API 一致
- **THEN** 系统报告所有数据均为最新，无需更新

### Requirement: 通过 API 端点查询数据版本状态

系统必须提供 `GET /api/data/status` API 端点，返回当前数据版本元信息，包括各数据源的文档数量、最后更新时间和游戏版本号。

#### Scenario: 查询已有数据的版本状态

- **WHEN** 客户端发送 `GET /api/data/status` 请求且数据已采集过
- **THEN** API 返回 200 响应，JSON body 包含 `last_updated`（ISO 8601 时间戳）、`game_version`（如 "7.40c"）和 `sources`（各数据源详情）

#### Scenario: 查询从未采集过数据的版本状态

- **WHEN** 客户端发送 `GET /api/data/status` 请求且从未执行过数据采集
- **THEN** API 返回 200 响应，JSON body 中 `last_updated` 为 null、`game_version` 为 null、`sources` 为空对象
