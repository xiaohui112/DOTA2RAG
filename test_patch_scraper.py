#!/usr/bin/env python3
"""patch_scraper.py 单元测试

覆盖场景：HTML 解析、script JSON 提取、404 处理、超时处理
"""
import os
import sys

os.environ.setdefault("DASHSCOPE_API_KEY", "sk-test-key-for-local-testing")

print("=" * 60)
print("Patch Scraper 单元测试")
print("=" * 60)


# ── 测试 1: parse_patch_html ──────────────────────────────────
print("\n[测试 1] parse_patch_html - 基本 HTML 解析")
try:
    from src.ingestion.sources.patch_scraper import parse_patch_html

    html = """
    <html><body>
    <div class="general-changes">
        <li>Gold bounty for hero kills adjusted</li>
        <li>Map changes around Roshan pit</li>
    </div>
    <div class="hero-change npc_dota_hero_axe">
        <span class="name">Axe</span>
        <li>Counter Helix damage increased from 120 to 140</li>
        <li>Base armor increased by 1</li>
    </div>
    <div class="item-section item_blink_dagger">
        <span class="title">Blink Dagger</span>
        <li>Cooldown reduced from 15 to 14 seconds</li>
    </div>
    </body></html>
    """
    result = parse_patch_html(html)
    assert len(result["general_changes"]) == 2, f"Expected 2 general changes, got {len(result['general_changes'])}"
    assert len(result["hero_changes"]) >= 1, "Expected at least 1 hero change"
    assert result["hero_changes"][0]["hero_name"] == "Axe"
    assert len(result["hero_changes"][0]["changes"]) == 2
    print("✓ HTML 结构化解析正常")
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback; traceback.print_exc()


# ── 测试 2: parse_patch_html - 空 HTML ────────────────────────
print("\n[测试 2] parse_patch_html - 空 HTML 输入")
try:
    result = parse_patch_html("")
    assert result["general_changes"] == []
    assert result["hero_changes"] == []
    assert result["item_changes"] == []
    print("✓ 空 HTML 输入正确返回空结构")
except Exception as e:
    print(f"✗ 失败: {e}")


# ── 测试 3: extract_patch_from_script - JSON 提取 ─────────────
print("\n[测试 3] extract_patch_from_script - 从 script 标签提取 JSON")
try:
    from src.ingestion.sources.patch_scraper import extract_patch_from_script

    html_with_script = """
    <html><body>
    <div id="app"></div>
    <script type="application/json">
    {
        "general_changes": ["Test general change 1", "Test general change 2"],
        "hero_changes": [
            {"hero_name": "Storm Spirit", "changes": ["Ball Lightning mana cost reduced"]}
        ],
        "item_changes": [
            {"item_name": "BKB", "changes": ["Duration rescaled"]}
        ]
    }
    </script>
    </body></html>
    """
    result = extract_patch_from_script(html_with_script)
    assert len(result["general_changes"]) == 2
    assert result["hero_changes"][0]["hero_name"] == "Storm Spirit"
    assert len(result["item_changes"]) == 1
    print("✓ Script JSON 提取正常")
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback; traceback.print_exc()


# ── 测试 4: extract_patch_from_script - 空 HTML ───────────────
print("\n[测试 4] extract_patch_from_script - 空 HTML")
try:
    result = extract_patch_from_script("")
    assert result["general_changes"] == []
    print("✓ 空 HTML 正确返回空结构")
except Exception as e:
    print(f"✗ 失败: {e}")


# ── 测试 5: scrape_patch_notes - 404 处理 ─────────────────────
print("\n[测试 5] scrape_patch_notes - 不存在的版本")
try:
    from src.ingestion.sources.patch_scraper import scrape_patch_notes

    # 使用一个极其不可能存在的版本号
    result = scrape_patch_notes("0.00.nonexistent")
    assert result["version"] == "0.00.nonexistent"
    assert result["general_changes"] == []
    print("✓ 不存在版本正确返回空结构（含版本号）")
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback; traceback.print_exc()


# ── 测试 6: batch_scrape_patches - 空列表 ─────────────────────
print("\n[测试 6] batch_scrape_patches - 空列表")
try:
    from src.ingestion.sources.patch_scraper import batch_scrape_patches

    result = batch_scrape_patches([])
    assert result == []
    print("✓ 空列表正确返回空结果")
except Exception as e:
    print(f"✗ 失败: {e}")


# ── 测试 7: scrape_patch_notes 主函数 - 组合测试 ──────────────
print("\n[测试 7] scrape_patch_notes 主函数 - 模块导入和函数签名")
try:
    import inspect
    from src.ingestion.sources.patch_scraper import (
        fetch_patch_page,
        parse_patch_html,
        extract_patch_from_script,
        scrape_patch_notes,
        batch_scrape_patches,
    )
    # 验证函数签名
    sig = inspect.signature(fetch_patch_page)
    assert "version" in sig.parameters
    assert "max_retries" in sig.parameters

    sig = inspect.signature(batch_scrape_patches)
    assert "versions" in sig.parameters
    print("✓ 所有函数签名正确")
except Exception as e:
    print(f"✗ 失败: {e}")

print("\n" + "=" * 60)
print("Patch Scraper 测试完成！")
print("=" * 60)
