## Why

Dota 2 已更新至 7.40 版本（含后续 7.40c 等子补丁），新增了英雄和大量平衡性改动。但本项目当前数据存在三个核心问题：（1）ChromaDB 中的数据是静态快照，从未自动更新；（2）唯一数据源 OpenDota API 是社区维护的，更新有延迟，可能尚未包含 7.40 的完整数据和新英雄；（3）补丁数据采集模块 `patches.py` 只获取版本号和日期，**完全缺失具体的英雄/物品/通用改动内容**，导致 RAG 无法回答任何关于版本变更的问题。需要立即修复数据采集能力，确保系统能反映最新游戏状态。

## What Changes

- 新增 **Dota 2 官方 Patch Notes 网页抓取**能力，从 `dota2.com/patches/<version>` 抓取结构化的补丁详细变更内容（英雄改动、物品改动、通用改动），弥补 OpenDota API 补丁数据的严重不足
- 新增 **数据版本追踪**机制，记录当前向量库中数据对应的游戏版本号和采集时间戳，支持查询数据新鲜度
- 修改 **数据采集管线**，支持增量更新（只采集新版本补丁、只更新有变化的英雄/物品），避免每次全量重刷；增加数据采集前后的版本比对和日志
- 修改 **补丁数据处理**，将 Patch Notes 从简单的版本号列表升级为包含完整变更内容的结构化文档，按英雄/物品/通用分类组织并正确分块入库
- 新增 **采集健康检查**端点，暴露当前数据版本、最后更新时间、各 Collection 文档数量等信息，方便运维监控

## Capabilities

### New Capabilities

- `patch-notes-scraper`: 从 Dota 2 官方网站抓取完整 Patch Notes 内容，解析 HTML 提取结构化变更数据（英雄改动、物品改动、通用改动），作为 OpenDota API 补丁数据的补充/替代数据源
- `data-version-tracking`: 数据版本追踪机制——在向量库元数据中记录对应的游戏版本号和采集时间戳，提供 API 端点查询数据新鲜度，支持判断是否需要更新

### Modified Capabilities

- `data-ingestion`: 补丁数据采集从仅获取版本号/日期升级为获取完整变更内容；增加增量更新模式（检测并仅采集新版本数据）；CLI 增加 `--check` 参数用于检查数据是否需要更新

## Impact

- **影响代码**：`src/ingestion/sources/patches.py`（重构补丁采集逻辑）、`src/ingestion/runner.py`（增加增量更新和版本追踪）、`src/api/routes/`（新增健康检查/版本查询端点）
- **新增依赖**：可能需要 `beautifulsoup4`（已在 requirements.txt）用于解析 Dota 2 官网 HTML；可能需要 `playwright` 或 `httpx` 抓取动态渲染页面
- **外部依赖**：新增对 `dota2.com/patches/` 官方网站的网络请求（需要处理可能的反爬和页面结构变更）
- **数据影响**：ChromaDB 中的 `patches` Collection 结构将发生变化（从简单版本条目变为详细变更文档），需要清空后重建
- **API 变更**：新增 `GET /api/data/status` 端点，无破坏性变更
