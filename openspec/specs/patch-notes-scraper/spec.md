## ADDED Requirements

### Requirement: 从 Dota 2 官网抓取 Patch Notes 页面

系统必须能从 Dota 2 官方网站 (`https://www.dota2.com/patches/<version>`) 抓取指定版本的 Patch Notes 完整 HTML 内容。系统必须使用 `httpx` 发送 HTTP 请求，设置合理的 User-Agent 头，并在请求之间保持 2-3 秒间隔以避免触发反爬机制。

#### Scenario: 成功抓取指定版本 Patch Notes

- **WHEN** 系统请求抓取版本 "7.40" 的 Patch Notes
- **THEN** 系统向 `https://www.dota2.com/patches/7.40` 发送 GET 请求，返回该页面的完整 HTML 内容

#### Scenario: 页面不存在时的错误处理

- **WHEN** 系统请求抓取不存在的版本（如 "9.99"）的 Patch Notes
- **THEN** 系统必须捕获 HTTP 404 错误，记录警告日志，并返回空结果而非抛出异常

#### Scenario: 网络超时处理

- **WHEN** 请求 Dota 2 官网超过 30 秒未响应
- **THEN** 系统必须超时中断，记录错误日志，并在最多重试 2 次后放弃该版本的抓取

### Requirement: 解析 Patch Notes HTML 提取结构化变更数据

系统必须从抓取的 Patch Notes HTML 中解析出结构化的变更数据。使用 `BeautifulSoup4` 解析 HTML，提取以下三个类别的变更内容：通用改动（General Changes）、英雄改动（Hero Changes）、物品改动（Item Changes）。每个类别包含变更条目的文本描述。

#### Scenario: 解析包含三类改动的大版本补丁

- **WHEN** 系统解析 7.40 版本的 Patch Notes HTML
- **THEN** 系统输出一个结构化字典，至少包含 `general_changes`、`hero_changes`、`item_changes` 三个键，每个键对应一个变更条目列表

#### Scenario: 解析仅包含平衡性调整的小版本补丁

- **WHEN** 系统解析 7.40b 等小版本补丁的 HTML，该页面可能不包含通用改动
- **THEN** 系统输出的 `general_changes` 为空列表，但 `hero_changes` 和 `item_changes` 正常提取

#### Scenario: 英雄改动按英雄名组织

- **WHEN** 系统解析包含多个英雄改动的 Patch Notes
- **THEN** `hero_changes` 必须按英雄名组织，输出格式为 `[{"hero_name": "Anti-Mage", "changes": ["改动1", "改动2"]}, ...]`

### Requirement: 从内嵌 JSON 数据中提取 Patch Notes（降级方案）

当 Dota 2 官网使用客户端渲染时，页面 HTML 中可能不包含可见的 Patch Notes 文本，但数据可能以 JSON 格式嵌入在 `<script>` 标签中。系统必须尝试从页面的内嵌 `<script>` 标签中查找并解析 JSON 格式的补丁数据。

#### Scenario: 页面数据嵌入在 script 标签中

- **WHEN** 系统抓取的 HTML 正文中无可见文本，但 `<script>` 标签包含 JSON 数据
- **THEN** 系统必须解析该 JSON 数据，从中提取等效的补丁变更内容

#### Scenario: 页面既无可见文本也无内嵌 JSON

- **WHEN** 系统无法从 HTML 中提取任何补丁数据（完全依赖客户端 JS 渲染）
- **THEN** 系统必须记录错误日志说明需要升级抓取方案，并返回空结果

### Requirement: 批量抓取多个版本的 Patch Notes

系统必须支持批量抓取多个版本的 Patch Notes。接受一个版本号列表作为输入，逐个抓取并解析，每次请求之间间隔 2-3 秒。

#### Scenario: 批量抓取 3 个版本

- **WHEN** 系统接收到版本列表 `["7.40", "7.40b", "7.40c"]`
- **THEN** 系统逐个抓取并解析这 3 个版本的 Patch Notes，返回 3 个结构化结果，总耗时至少 4 秒（2 次间隔）

#### Scenario: 批量抓取中某个版本失败

- **WHEN** 批量抓取 `["7.40", "7.40b", "7.40c"]` 时 "7.40b" 页面返回 404
- **THEN** 系统跳过 "7.40b"，继续抓取 "7.40c"，最终返回 2 个成功结果并记录 1 条警告日志
