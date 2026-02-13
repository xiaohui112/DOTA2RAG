#!/usr/bin/env python3
"""chunk_patch_notes() 单元测试

验证分块策略：类别拆分、英雄二次拆分、元数据完整性
"""
import os
import sys

os.environ.setdefault("DASHSCOPE_API_KEY", "sk-test-key-for-local-testing")

print("=" * 60)
print("chunk_patch_notes 单元测试")
print("=" * 60)


# ── 测试 1: 基本分类拆分 ──────────────────────────────────────
print("\n[测试 1] 基本分类拆分 - 通用/英雄/物品")
try:
    from src.ingestion.processors.chunker import chunk_patch_notes

    patch_data = {
        "name": "7.40",
        "date": "2026-01-15",
        "general_changes": [
            "Gold bounty for hero kills adjusted",
            "Map changes around Roshan pit",
        ],
        "hero_changes": [
            {
                "hero_name": "Axe",
                "changes": ["Counter Helix damage increased"],
            },
        ],
        "item_changes": [
            {
                "item_name": "Blink Dagger",
                "changes": ["Cooldown reduced"],
            },
        ],
    }

    chunks = chunk_patch_notes(patch_data)
    assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"

    # 检查各类别
    categories = [c["metadata"]["change_category"] for c in chunks]
    assert "general" in categories
    assert "hero" in categories
    assert "item" in categories
    print(f"✓ 正确拆分为 {len(chunks)} 个 chunk: {categories}")

except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback; traceback.print_exc()


# ── 测试 2: 元数据完整性 ──────────────────────────────────────
print("\n[测试 2] 元数据完整性")
try:
    patch_data = {
        "name": "7.40c",
        "date": "2026-02-01",
        "general_changes": ["Test change"],
        "hero_changes": [],
        "item_changes": [],
    }

    chunks = chunk_patch_notes(patch_data)
    assert len(chunks) == 1

    meta = chunks[0]["metadata"]
    assert meta["patch_version"] == "7.40c"
    assert meta["change_category"] == "general"
    assert meta["source"] == "patch"
    assert meta["category"] == "patch"
    assert "entity_name" in meta
    print(f"✓ 元数据完整: patch_version={meta['patch_version']}, "
          f"change_category={meta['change_category']}")

except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback; traceback.print_exc()


# ── 测试 3: 英雄二次拆分 ──────────────────────────────────────
print("\n[测试 3] 英雄改动超过 1500 字符时的二次拆分")
try:
    # 构造超过 1500 字符的英雄改动
    long_changes = [f"Change {i}: very long description text that makes this even longer" for i in range(30)]
    patch_data = {
        "name": "7.40",
        "date": "2026-01-15",
        "general_changes": [],
        "hero_changes": [
            {"hero_name": "Axe", "changes": long_changes[:15]},
            {"hero_name": "Invoker", "changes": long_changes[15:]},
        ],
        "item_changes": [],
    }

    chunks = chunk_patch_notes(patch_data)

    # 应该有 2 个 chunk（按英雄拆分）
    hero_chunks = [c for c in chunks if c["metadata"]["change_category"] == "hero"]
    assert len(hero_chunks) == 2, f"Expected 2 hero chunks, got {len(hero_chunks)}"

    hero_names = [c["metadata"].get("hero_name") for c in hero_chunks]
    assert "Axe" in hero_names
    assert "Invoker" in hero_names
    print(f"✓ 英雄改动正确按英雄名拆分: {hero_names}")

except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback; traceback.print_exc()


# ── 测试 4: 英雄改动未超阈值（不拆分） ───────────────────────
print("\n[测试 4] 英雄改动未超 1500 字符时不拆分")
try:
    patch_data = {
        "name": "7.40b",
        "date": "2026-01-20",
        "general_changes": [],
        "hero_changes": [
            {"hero_name": "Axe", "changes": ["Small fix"]},
            {"hero_name": "CM", "changes": ["Small buff"]},
        ],
        "item_changes": [],
    }

    chunks = chunk_patch_notes(patch_data)
    hero_chunks = [c for c in chunks if c["metadata"]["change_category"] == "hero"]
    assert len(hero_chunks) == 1, f"Expected 1 hero chunk, got {len(hero_chunks)}"
    assert "hero_name" not in hero_chunks[0]["metadata"]
    print("✓ 短英雄改动正确合并为 1 个 chunk")

except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback; traceback.print_exc()


# ── 测试 5: 空补丁数据（降级到基础条目） ─────────────────────
print("\n[测试 5] 无详细内容时降级为基础版本条目")
try:
    patch_data = {
        "name": "7.39",
        "date": "2025-12-01",
        "general_changes": [],
        "hero_changes": [],
        "item_changes": [],
    }

    chunks = chunk_patch_notes(patch_data)
    assert len(chunks) == 1
    assert "7.39" in chunks[0]["content"]
    assert chunks[0]["metadata"]["change_category"] == "summary"
    print("✓ 空内容正确降级为基础版本条目")

except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback; traceback.print_exc()


# ── 测试 6: 内容完整性 ────────────────────────────────────────
print("\n[测试 6] chunk 内容包含正确信息")
try:
    patch_data = {
        "name": "7.40",
        "date": "2026-01-15",
        "general_changes": ["Gold bounty changed", "Map updated"],
        "hero_changes": [],
        "item_changes": [],
    }

    chunks = chunk_patch_notes(patch_data)
    content = chunks[0]["content"]
    assert "7.40" in content
    assert "Gold bounty changed" in content
    assert "Map updated" in content
    assert "通用改动" in content
    print("✓ 内容包含版本号和所有改动")

except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback; traceback.print_exc()


print("\n" + "=" * 60)
print("chunk_patch_notes 测试完成！")
print("=" * 60)
