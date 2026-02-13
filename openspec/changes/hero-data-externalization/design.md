## Context

当前 `src/ingestion/sources/heroes.py` 中硬编码了两大字典：

- `HERO_NICKNAMES`: 120+ 条英雄内部名 → 常用简称列表的映射
- `HERO_RELEASE_VERSIONS`: 120+ 条英雄内部名 → 上线版本号的映射

这些数据本质上是知识库的"元数据"，不是程序逻辑。每次新英雄上线（如朗戈 hero_id=155），都需要修改 Python 源码才能补充元数据。此外，`fetch_heroes()` 的接口已经从原来仅调 OpenDota 改为调用官方 `herolist` + `herodata` API，`runner.py` 中的 `ingest_heroes()` 仍然引用 `localized_name` 字段，需要适配。

## Goals / Non-Goals

**Goals:**

- 将 `HERO_NICKNAMES` 和 `HERO_RELEASE_VERSIONS` 移出代码，存为 `data/` 下的 JSON 文件
- `heroes.py` 在运行时从 JSON 文件加载映射，缺失文件时优雅降级（空映射，不报错）
- 新英雄上线后只需编辑 JSON 文件即可补充元数据，无需改代码
- 确保所有英雄（包括朗戈等最新英雄）在 `fetch_heroes()` 中都能正常获取
- `runner.py` 中 `ingest_heroes()` 适配新的 `fetch_heroes()` 返回字段

**Non-Goals:**

- 不引入数据库（SQLite/Postgres 等），JSON 文件已足够满足当前规模
- 不提供 Web UI 编辑元数据的能力
- 不自动从第三方数据源抓取简称（简称需要人工维护，因为是社区俗语）

## Decisions

### 决策 1：使用 JSON 文件而非数据库

**选择**: `data/hero_nicknames.json` 和 `data/hero_release_versions.json`

**理由**: 当前英雄总数约 130 个，数据量极小。JSON 文件可直接 git 管理，团队成员可 PR 方式补充新英雄简称。如果未来规模扩大到需要复杂查询（如搜索简称反查英雄），可再考虑 SQLite。

**替代方案**: SQLite → 增加依赖和维护成本，对当前规模过度设计。

### 决策 2：JSON 文件格式

**`data/hero_nicknames.json`**:
```json
{
  "npc_dota_hero_antimage": ["AM", "敌法", "敌法师"],
  "npc_dota_hero_largo": ["朗戈", "蛙", "LARGO"]
}
```
Key 使用英雄内部名（`npc_dota_hero_xxx`），与官方 API 返回的 `name` 字段一致，便于直接查询。

**`data/hero_release_versions.json`**:
```json
{
  "npc_dota_hero_antimage": "6.00",
  "npc_dota_hero_largo": "7.38"
}
```

### 决策 3：加载策略 — 懒加载 + 缓存

文件在首次调用 `_get_hero_nicknames()` / `_find_hero_release_version()` 时加载一次，缓存到模块级变量。后续调用直接读缓存。如果文件不存在或解析失败，返回空字典并记录 warning 日志。

**理由**: 与现有 `patch_scraper.py` 中 `_load_hero_id_map()` 的缓存模式一致。

### 决策 4：runner.py 适配

`ingest_heroes()` 中原来用 `hero.get("localized_name")` 获取英雄名，新接口返回的是 `name_loc`。需要修改为优先取 `name_loc`，降级到 `name_english_loc`，最后到 `name`。

## Risks / Trade-offs

- **[JSON 文件可能被误删]** → 降级为空映射，不影响核心数据获取功能。英雄依然能被采集，只是缺少简称/版本元数据。日志会打印 warning 提醒。
- **[新英雄简称维护滞后]** → 这是不可避免的（简称是社区约定俗成的），但至少现在修改 JSON 文件比改代码方便得多。
- **[官方 API 获取英雄详情需逐个请求，127 个英雄约需 60+ 秒]** → 可通过 `include_details=False` 跳过详情获取，仅做简单列表更新。批量获取策略已有 0.5s 间隔控制。
