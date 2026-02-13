#!/usr/bin/env python3
"""基础功能测试脚本"""
import os
import sys

# 设置临时 API Key（仅用于测试）
os.environ.setdefault("DASHSCOPE_API_KEY", "sk-test-key-for-local-testing")

print("=" * 60)
print("Dota 2 RAG 服务 - 基础功能测试")
print("=" * 60)

# 测试 1: 配置加载
print("\n[测试 1] 配置管理模块")
try:
    from config.settings import settings
    print(f"✓ 配置加载成功")
    print(f"  - API Base URL: {settings.API_BASE_URL}")
    print(f"  - Embedding 模型: {settings.EMBEDDING_MODEL}")
    print(f"  - Chat 模型: {settings.CHAT_MODEL}")
    print(f"  - ChromaDB 路径: {settings.CHROMA_PERSIST_DIR}")
    print(f"  - API 端口: {settings.API_PORT}")
    print(f"  - 缓存 TTL: {settings.CACHE_TTL} 秒")
except Exception as e:
    print(f"✗ 配置加载失败: {e}")
    sys.exit(1)

# 测试 2: 数据清洗器
print("\n[测试 2] 数据清洗模块")
try:
    from src.ingestion.processors.cleaner import (
        clean_html,
        normalize_whitespace,
        normalize_number,
        add_metadata,
    )
    
    # 测试 HTML 清洗
    html_text = "<p>测试文本 <b>加粗</b> 内容</p>"
    cleaned = clean_html(html_text)
    assert "测试文本" in cleaned and "<b>" not in cleaned
    print("✓ HTML 清洗功能正常")
    
    # 测试空白字符标准化
    messy_text = "多  个   空格\n\n换行"
    normalized = normalize_whitespace(messy_text)
    assert "  " not in normalized
    print("✓ 空白字符标准化功能正常")
    
    # 测试数值标准化
    assert normalize_number("123.45") == 123.45
    assert normalize_number(100) == 100.0
    print("✓ 数值标准化功能正常")
    
    # 测试元数据添加
    data = {"name": "测试实体"}
    data_with_meta = add_metadata(data, "api", "hero", "测试英雄")
    assert "metadata" in data_with_meta
    assert data_with_meta["metadata"]["source"] == "api"
    print("✓ 元数据添加功能正常")
    
except Exception as e:
    print(f"✗ 数据清洗模块测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 3: 文档分块器
print("\n[测试 3] 文档分块模块")
try:
    from src.ingestion.processors.chunker import (
        chunk_hero_item,
        chunk_wiki_article,
    )
    
    # 测试英雄数据分块
    hero_data = {
        "name": "Anti-Mage",
        "localized_name": "敌法师",
        "primary_attr": "agi",
        "attack_type": "Melee",
        "roles": ["Carry", "Escape"],
        "base_str": 21,
        "str_gain": 1.6,
        "metadata": {"source": "api", "category": "hero"},
    }
    chunks = chunk_hero_item(hero_data, "hero")
    assert len(chunks) == 1
    assert "敌法师" in chunks[0]["content"]
    print("✓ 英雄数据分块功能正常")
    
    # 测试 Wiki 文章分块（短文本）
    wiki_data = {
        "content": "这是一个测试文章。内容比较短，不需要分割。",
        "metadata": {"source": "wiki", "category": "mechanic"},
    }
    chunks = chunk_wiki_article(wiki_data, chunk_size=20, overlap=5)
    assert len(chunks) >= 1
    print(f"✓ Wiki 文章分块功能正常（生成了 {len(chunks)} 个块）")
    
except Exception as e:
    print(f"✗ 文档分块模块测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 4: HTTP 客户端（不实际调用 API）
print("\n[测试 4] HTTP 客户端模块")
try:
    from src.ingestion.sources.http_client import RateLimitedClient
    print("✓ HTTP 客户端模块导入成功")
except Exception as e:
    print(f"✗ HTTP 客户端模块测试失败: {e}")

# 测试 5: 向量存储模块（不实际连接 ChromaDB）
print("\n[测试 5] 向量存储模块")
try:
    from src.vectorstore.embeddings import DashScopeEmbeddings, get_embeddings
    print("✓ Embedding 模块导入成功")
    
    from src.vectorstore.store import VectorStore, COLLECTIONS
    print(f"✓ 向量存储模块导入成功，支持的 Collection: {list(COLLECTIONS.values())}")
    
except Exception as e:
    print(f"✗ 向量存储模块测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 6: 数据源模块导入
print("\n[测试 6] 数据源模块")
try:
    from src.ingestion.sources import fetch_heroes, fetch_items
    print("✓ 数据源模块导入成功")
except Exception as e:
    print(f"✗ 数据源模块测试失败: {e}")

print("\n" + "=" * 60)
print("基础功能测试完成！")
print("=" * 60)
print("\n注意：")
print("- 以上测试仅验证模块导入和基础功能")
print("- 实际 API 调用（OpenDota、DashScope）需要有效的 API Key")
print("- ChromaDB 初始化需要实际运行时才会创建数据库文件")
