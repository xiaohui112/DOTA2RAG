## 1. Patch Notes 抓取模块（patch-notes-scraper）

- [x] 1.1 创建 `src/ingestion/sources/patch_scraper.py`——实现 `fetch_patch_page(version: str) -> str` 函数，使用 httpx 从 `dota2.com/patches/<version>` 抓取 HTML，设置 User-Agent 头，30 秒超时，失败最多重试 2 次
- [x] 1.2 实现 `parse_patch_html(html: str) -> dict` 函数——使用 BeautifulSoup4 解析 HTML，提取 `general_changes`、`hero_changes`、`item_changes` 三个类别的结构化变更数据，英雄改动按英雄名组织
- [x] 1.3 实现 `extract_patch_from_script(html: str) -> dict` 降级方案——当 HTML 正文无可见文本时，从 `<script>` 标签中查找并解析内嵌 JSON 数据
- [x] 1.4 实现 `scrape_patch_notes(version: str) -> dict` 主函数——组合抓取 + 解析（优先 HTML 解析，降级到 script JSON），返回结构化结果或空字典
- [x] 1.5 实现 `batch_scrape_patches(versions: List[str]) -> List[dict]` 批量抓取函数——逐个抓取版本列表，每次请求间隔 2-3 秒，单个版本失败不影响其他版本

## 2. 数据版本追踪模块（data-version-tracking）

- [x] 2.1 创建 `src/ingestion/version_tracker.py`——实现 `VersionTracker` 类，管理 `data/version_meta.json` 的读写
- [x] 2.2 实现 `read_version_meta() -> dict` 方法——读取 JSON 文件，文件不存在返回默认空结构，文件损坏时记录警告并重建
- [x] 2.3 实现 `update_source_meta(source: str, count: int, **extra)` 方法——更新单个数据源的 count、updated_at 字段，以及全局的 last_updated
- [x] 2.4 实现 `check_freshness() -> dict` 方法——查询 OpenDota API 获取远程数据源计数和补丁列表，与本地元信息比对，返回各数据源的更新状态摘要

## 3. 重构补丁数据采集流程（data-ingestion 修改）

- [x] 3.1 重构 `src/ingestion/sources/patches.py` 中的 `fetch_patches()` 函数——整合 OpenDota API 版本列表 + patch_scraper 官网详细内容抓取，返回包含完整变更内容的补丁数据列表
- [x] 3.2 实现增量补丁采集——`fetch_patches()` 接受可选的 `since_version` 参数，仅获取该版本之后的新补丁
- [x] 3.3 实现官网抓取失败时的降级逻辑——官网不可用时自动降级为仅保存 OpenDota 的版本号+日期，记录警告日志

## 4. 补丁数据分块策略升级

- [x] 4.1 在 `src/ingestion/processors/chunker.py` 中新增 `chunk_patch_notes(patch_data: dict) -> List[dict]` 函数——将补丁按类别（通用/英雄/物品）拆分为多个 chunk
- [x] 4.2 实现英雄改动的二次拆分逻辑——当英雄改动部分超过 1500 字符时，按英雄名进一步拆分为独立 chunk
- [x] 4.3 为每个补丁 chunk 添加元数据——包含 `patch_version`、`change_category`（general/hero/item）、可选的 `hero_name`

## 5. 更新 Runner 和 CLI

- [x] 5.1 重构 `src/ingestion/runner.py` 中的 `ingest_patches()` 函数——使用新的 `fetch_patches()` 和 `chunk_patch_notes()` 替换原有的简单文本拼接
- [x] 5.2 在 `run_ingest()` 中集成 `VersionTracker`——每个数据源采集完成后调用 `update_source_meta()` 更新版本元信息
- [x] 5.3 CLI 新增 `--incremental` 参数——调用 `check_freshness()` 后仅采集有变化的数据源
- [x] 5.4 CLI 新增 `--check` 参数——调用 `check_freshness()` 输出更新状态摘要，不执行采集

## 6. API 端点扩展

- [x] 6.1 在 `src/api/schemas.py` 中新增 `DataStatusResponse` Pydantic 模型——包含 `last_updated`、`game_version`、`sources` 字段
- [x] 6.2 在 `src/api/routes/` 中新增 `GET /api/data/status` 端点——读取 `version_meta.json` 返回数据版本状态
- [x] 6.3 在 `src/api/main.py` 中注册新路由

## 7. 测试与验证

- [x] 7.1 为 `patch_scraper.py` 编写单元测试——覆盖 HTML 解析、script JSON 提取、404 处理、超时处理场景
- [x] 7.2 为 `version_tracker.py` 编写单元测试——覆盖读取/写入/损坏恢复/新鲜度检查场景
- [x] 7.3 为 `chunk_patch_notes()` 编写单元测试——验证分块策略（类别拆分、英雄二次拆分、元数据完整性）
- [x] 7.4 手动执行一次 `python -m src.ingestion.runner --check` 验证数据检查功能
- [x] 7.5 手动执行一次 `python -m src.ingestion.runner --all` 验证全量采集并检查 `version_meta.json` 生成正确
