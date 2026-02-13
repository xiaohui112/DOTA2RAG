## Why

英雄数据（简称、上线版本等）目前硬编码在 `src/ingestion/sources/heroes.py` 中，代码中维护了 120+ 条英雄简称映射和版本映射，导致：
1. **维护困难**：新英雄（如朗戈/Largo）上线后需要修改代码才能补全简称，数据与逻辑耦合严重
2. **数据不完整**：知识库应该把这些元数据视为"数据"而非"代码"，方便随时扩展和更新
3. **新英雄遗漏**：硬编码方式无法自动覆盖新上线英雄，导致朗戈等最新英雄缺少简称等信息

## What Changes

- 将英雄简称映射（`HERO_NICKNAMES`）从 Python 代码中移除，改为 `data/hero_nicknames.json` 数据文件
- 将英雄上线版本映射（`HERO_RELEASE_VERSIONS`）从 Python 代码中移除，改为 `data/hero_release_versions.json` 数据文件
- 修改 `heroes.py` 从数据文件中加载这些映射，而非硬编码
- 确保所有英雄（包括朗戈 hero_id=155 等最新英雄）在 `fetch_heroes()` 中都能被正确获取和处理
- 提供便捷的数据文件更新方式，便于后续新英雄上线时快速补充元数据

## Capabilities

### New Capabilities
- `hero-metadata-store`: 英雄元数据（简称、上线版本等）外部化存储管理，包括从 JSON 文件加载映射、数据文件格式定义和缺失数据的容错处理

### Modified Capabilities
- `data-ingestion`: 英雄数据采集需要从外部数据文件读取简称/版本映射，而非依赖硬编码字典；需确保所有英雄（包括最新上线的英雄如朗戈）都能被正确获取

## Impact

- **代码变更**: `src/ingestion/sources/heroes.py` — 移除硬编码字典，改为从文件加载
- **新增数据文件**: `data/hero_nicknames.json`, `data/hero_release_versions.json`
- **下游影响**: `src/ingestion/runner.py` 中 `ingest_heroes()` 调用方式需适配新的 `fetch_heroes()` 接口
- **无 Breaking Change**: 对外接口 `fetch_heroes()` 返回格式不变，仅数据来源从硬编码改为文件
