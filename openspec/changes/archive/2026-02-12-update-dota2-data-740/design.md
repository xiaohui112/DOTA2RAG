## Context

本项目是一个 Dota 2 RAG 问答服务，使用 OpenDota API 作为唯一数据源，通过 `src/ingestion/` 模块采集英雄、物品、技能、补丁和 Wiki 数据，经清洗分块后存入 ChromaDB 向量库。当前存在以下问题：

- **补丁数据严重不足**：`patches.py` 仅从 OpenDota `/api/constants/patch` 获取版本号和日期，不包含任何具体变更内容。`ingest_patches()` 生成的文档仅为 `"版本: 7.xx\n发布日期: xxx"` 格式，对 RAG 问答毫无价值。
- **数据源单一且有延迟**：OpenDota API 是社区维护的，新版本发布后数据更新可能滞后数天到数周。
- **无版本追踪**：不知道向量库中的数据对应哪个游戏版本，也没有机制判断是否需要更新。
- **无增量能力**：每次采集都是全量覆盖，对大型数据集（200+ 物品、120+ 英雄）效率低下。

技术栈：Python、FastAPI、LangChain、ChromaDB、httpx、BeautifulSoup4（已在 requirements.txt）。

## Goals / Non-Goals

**Goals:**

- 实现从 Dota 2 官方网站抓取完整 Patch Notes 变更内容，使 RAG 能回答 "7.40 改了什么" 类问题
- 建立数据版本追踪机制，一目了然地知道数据是否过期
- 实现增量更新，只采集新补丁和变更数据，避免不必要的全量重刷
- 新增 API 端点暴露数据版本状态，便于运维和自动化

**Non-Goals:**

- 不做自动定时更新（cron/scheduler）——本次仅实现手动触发的更新能力，定时调度作为后续需求
- 不做 Dota 2 Wiki 深度爬虫——Wiki 数据目前用 OpenDota constants 替代，本次不改动
- 不做数据回滚能力——向量库不保留历史版本快照
- 不做多语言 Patch Notes 支持——仅采集英文版本

## Decisions

### Decision 1: Patch Notes 数据源选择

**选择**: 优先使用 Dota 2 官方网站 (`dota2.com/patches/<version>`) 抓取，OpenDota API 作为补丁列表的索引来源。

**替代方案**:
- (A) 纯 OpenDota API：当前方案，但 `/api/constants/patch` 不包含变更详情，且没有其他端点提供 patch notes 全文
- (B) Steam Web API：没有公开的 patch notes 端点
- (C) 社区 Wiki（Liquipedia/Dota 2 Wiki）：数据结构不稳定，爬取成本高

**理由**: Dota 2 官方网站是唯一权威且结构相对稳定的 Patch Notes 来源。使用 OpenDota 的 `/api/constants/patch` 获取所有版本列表（带版本号），再逐个从官网抓取详细内容，两者互补。

### Decision 2: 网页抓取技术方案

**选择**: 使用 `httpx` + `BeautifulSoup4` 抓取，不引入 Playwright/Selenium。

**替代方案**:
- (A) Playwright：支持 JS 渲染，但依赖重（需要浏览器二进制文件），不适合 Docker 部署
- (B) Selenium：同上，且更慢

**理由**: Dota 2 官网的 patches 页面虽然是 React SPA，但页面数据通常在初始 HTML 或内联 `<script>` 标签中以 JSON 形式嵌入（SSR 或 preload data 模式）。先尝试 httpx 直接请求，如果发现需要 JS 渲染再降级考虑其他方案。`beautifulsoup4` 和 `httpx` 已在项目依赖中，零额外成本。

### Decision 3: 数据版本追踪存储

**选择**: 使用本地 JSON 文件 (`data/version_meta.json`) 存储版本追踪元数据。

**替代方案**:
- (A) 存入 ChromaDB 专门的 Collection：过于复杂，版本元数据不需要向量检索
- (B) SQLite：引入额外依赖，小数据量不值得
- (C) 环境变量/配置文件：不适合动态更新的数据

**理由**: 版本追踪数据量极小（JSON < 1KB），结构简单（各数据源的版本号 + 时间戳 + 文档计数），读写频率低。JSON 文件足以满足需求，且易于人工检查和调试。

**文件结构**:
```json
{
  "last_updated": "2026-02-12T10:30:00Z",
  "game_version": "7.40c",
  "sources": {
    "heroes": {"count": 126, "updated_at": "2026-02-12T10:30:00Z"},
    "items": {"count": 208, "updated_at": "2026-02-12T10:30:00Z"},
    "patches": {"count": 45, "updated_at": "2026-02-12T10:30:00Z", "latest_patch": "7.40c"},
    "abilities": {"count": 650, "updated_at": "2026-02-12T10:30:00Z"},
    "wiki": {"count": 5, "updated_at": "2026-02-12T10:30:00Z"}
  }
}
```

### Decision 4: 增量更新策略

**选择**: 基于版本号比对的增量更新。

- **补丁数据**：比对本地 `version_meta.json` 中的 `latest_patch` 与 OpenDota API 返回的补丁列表，只抓取新版本的 Patch Notes
- **英雄/物品/技能数据**：比对本地记录的文档数量与 API 返回的数量。数量变化时触发全量重刷该类别（因为 OpenDota 不提供变更时间戳，无法精确增量）
- CLI 新增 `--check` 参数：仅检查是否有更新，不执行采集，输出差异摘要

**理由**: 补丁数据天然具有版本号，适合增量。英雄/物品数据在 OpenDota API 中没有 `updated_at` 字段，无法精确判断哪条记录变了，但数量变化（新英雄/新物品）是可靠的触发信号。

### Decision 5: Patch Notes 解析与分块策略

**选择**: 每个补丁版本输出多个文档块——按类别拆分为"通用改动"、"英雄改动"、"物品改动"三个主要 chunk，大的英雄改动部分进一步按英雄名拆分。

**替代方案**:
- (A) 每个版本一个文档：内容过长（7.xx 大版本 patch notes 可达数千字），向量检索效果差
- (B) 固定字符数递归分割：会切断语义完整的英雄/物品改动描述

**理由**: Patch Notes 具有天然的层级结构（版本 → 类别 → 具体条目）。按类别拆分既保持语义完整，又控制了文档长度。英雄改动部分如果过长（大版本），进一步按英雄拆分确保每个 chunk 信息密度适中。

### Decision 6: API 端点设计

**选择**: 新增 `GET /api/data/status` 端点，返回 `version_meta.json` 的内容，复用现有 `health.py` 路由模块。

**理由**: 与现有的 `/api/health` 和 `/api/stats` 保持一致的 API 风格。不需要新建路由文件，扩展 `health.py` 或新增 `data.py` 路由即可。

## Risks / Trade-offs

**[风险] Dota 2 官网页面结构变更** → 定期维护解析器。Patch Notes 页面结构可能随 Valve 网站改版而变化。将解析逻辑封装为独立函数，便于快速修复。首次实现后添加一个验证测试用例。

**[风险] 官网反爬/Cloudflare 保护** → 设置合理的 User-Agent 和请求间隔（2-3 秒），不并发请求。如果被封，降级到仅使用 OpenDota 数据。

**[风险] OpenDota API 数据延迟导致新英雄缺失** → 短期内无法完全解决。增加数据状态端点后，用户可以快速识别缺失。未来可考虑从 Valve 的 Steam Web API 获取英雄列表作为补充。

**[权衡] JSON 文件 vs 数据库存储版本信息** → JSON 文件不支持并发写入。但本项目只有单实例运行，不存在并发采集场景，简单性优先。

**[权衡] 增量更新不精确** → 英雄/物品数据无法精确增量（只能检测数量变化），可能漏更新已有英雄的属性调整。接受这个限制，用户可通过 `--source heroes` 手动触发全量刷新。
