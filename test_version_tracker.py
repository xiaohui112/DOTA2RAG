#!/usr/bin/env python3
"""version_tracker.py 单元测试

覆盖场景：读取/写入/损坏恢复/新鲜度检查
"""
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("DASHSCOPE_API_KEY", "sk-test-key-for-local-testing")

print("=" * 60)
print("Version Tracker 单元测试")
print("=" * 60)


# ── 测试 1: read_version_meta - 文件不存在 ────────────────────
print("\n[测试 1] read_version_meta - 文件不存在")
try:
    from src.ingestion.version_tracker import VersionTracker

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = VersionTracker(meta_path=Path(tmpdir) / "nonexistent.json")
        meta = tracker.read_version_meta()
        assert meta["last_updated"] is None
        assert meta["game_version"] is None
        assert meta["sources"] == {}
        print("✓ 文件不存在时正确返回默认空结构")
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback; traceback.print_exc()


# ── 测试 2: read_version_meta - 正常文件 ──────────────────────
print("\n[测试 2] read_version_meta - 正常 JSON 文件")
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / "version_meta.json"
        test_data = {
            "last_updated": "2026-01-01T00:00:00+00:00",
            "game_version": "7.35",
            "sources": {
                "heroes": {"count": 125, "updated_at": "2026-01-01T00:00:00+00:00"},
            },
        }
        meta_path.write_text(json.dumps(test_data, ensure_ascii=False))

        tracker = VersionTracker(meta_path=meta_path)
        meta = tracker.read_version_meta()
        assert meta["game_version"] == "7.35"
        assert meta["sources"]["heroes"]["count"] == 125
        print("✓ 正常文件读取成功")
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback; traceback.print_exc()


# ── 测试 3: read_version_meta - 文件损坏 ──────────────────────
print("\n[测试 3] read_version_meta - 损坏的 JSON 文件")
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / "version_meta.json"
        meta_path.write_text("{ broken json ,,, }")

        tracker = VersionTracker(meta_path=meta_path)
        meta = tracker.read_version_meta()
        assert meta["last_updated"] is None
        assert meta["sources"] == {}
        # 检查文件是否被重建
        assert meta_path.exists()
        rebuilt = json.loads(meta_path.read_text())
        assert rebuilt["sources"] == {}
        print("✓ 损坏文件正确恢复并重建")
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback; traceback.print_exc()


# ── 测试 4: update_source_meta ────────────────────────────────
print("\n[测试 4] update_source_meta - 更新数据源元信息")
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / "version_meta.json"
        tracker = VersionTracker(meta_path=meta_path)

        # 第一次写入
        tracker.update_source_meta("heroes", 126)
        meta = tracker.read_version_meta()
        assert meta["sources"]["heroes"]["count"] == 126
        assert meta["sources"]["heroes"]["updated_at"] is not None
        assert meta["last_updated"] is not None
        print("  ✓ 首次写入成功")

        # 更新 patches（带 extra 参数）
        tracker.update_source_meta("patches", 45, latest_patch="7.40c")
        meta = tracker.read_version_meta()
        assert meta["sources"]["patches"]["count"] == 45
        assert meta["sources"]["patches"]["latest_patch"] == "7.40c"
        assert meta["game_version"] == "7.40c"
        print("  ✓ 带 latest_patch 更新成功，game_version 同步更新")

        # 再次更新 heroes 不应影响 patches
        tracker.update_source_meta("heroes", 127)
        meta = tracker.read_version_meta()
        assert meta["sources"]["heroes"]["count"] == 127
        assert meta["sources"]["patches"]["count"] == 45
        print("  ✓ 更新单个数据源不影响其他数据源")

        print("✓ update_source_meta 全部通过")
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback; traceback.print_exc()


# ── 测试 5: check_freshness 基础调用 ──────────────────────────
print("\n[测试 5] check_freshness - 基础调用（需要网络）")
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / "version_meta.json"
        tracker = VersionTracker(meta_path=meta_path)

        result = tracker.check_freshness()
        assert "needs_update" in result
        assert "details" in result
        assert isinstance(result["details"], dict)

        # 没有本地数据，应该报告需要更新
        if result.get("needs_update"):
            print(f"  ✓ 检测到需要更新（预期，因为本地数据为空）")
        else:
            print(f"  ⚠ 未报告需要更新（可能是网络问题）")

        # 打印各数据源状态
        for name, detail in result.get("details", {}).items():
            print(f"    {name}: {detail.get('message', '未知')}")

        print("✓ check_freshness 基础调用正常")
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback; traceback.print_exc()


# ── 测试 6: check_freshness 有本地数据时 ──────────────────────
print("\n[测试 6] check_freshness - 有本地数据时的比对")
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / "version_meta.json"
        tracker = VersionTracker(meta_path=meta_path)

        # 写入一些假的本地数据（数量设为极高以确保不需要更新英雄）
        tracker.update_source_meta("heroes", 999)
        tracker.update_source_meta("items", 999)
        tracker.update_source_meta("patches", 999, latest_patch="99.99z")

        result = tracker.check_freshness()
        details = result.get("details", {})

        # 英雄和物品数量比远程多，不应该需要更新
        # patches 的 latest_patch 不存在于远程列表，会降级为全部缺失
        if "heroes" in details:
            print(f"    heroes: local={details['heroes'].get('local')}, remote={details['heroes'].get('remote')}")
        if "patches" in details:
            print(f"    patches: local_latest={details['patches'].get('local_latest')}")

        print("✓ 有本地数据时 check_freshness 正常运行")
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback; traceback.print_exc()


print("\n" + "=" * 60)
print("Version Tracker 测试完成！")
print("=" * 60)
