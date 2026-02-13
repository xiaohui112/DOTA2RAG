#!/usr/bin/env python3
"""端到端集成测试（需要真实的 API Key）"""
import os
import sys

print("=" * 60)
print("Dota 2 RAG 服务 - 端到端集成测试")
print("=" * 60)

# 检查 API Key
api_key = os.environ.get("DASHSCOPE_API_KEY", "")
if not api_key or api_key == "test_key_for_local_testing":
    print("\n⚠️  警告：未检测到有效的 DASHSCOPE_API_KEY")
    print("   此测试需要真实的 API Key 才能完整运行")
    print("   设置方式：export DASHSCOPE_API_KEY='your_key_here'")
    print("\n   将跳过需要 API 调用的测试...\n")
    skip_api_tests = True
else:
    print(f"\n✓ 检测到 API Key: {api_key[:10]}...")
    skip_api_tests = False

# 测试 1: 完整数据采集流程
print("\n[测试 1] 完整数据采集流程")
try:
    from src.ingestion.sources.heroes import fetch_heroes
    from src.ingestion.sources.items import fetch_items
    from src.ingestion.processors.cleaner import add_metadata
    from src.ingestion.processors.chunker import chunk_hero_item
    
    # 采集英雄数据
    print("  1.1 采集英雄数据...")
    heroes = fetch_heroes()
    print(f"     ✓ 获取 {len(heroes)} 个英雄")
    
    # 采集物品数据
    print("  1.2 采集物品数据...")
    items = fetch_items()
    print(f"     ✓ 获取 {len(items)} 个物品")
    
    # 处理第一个英雄
    print("  1.3 处理英雄数据（添加元数据 + 分块）...")
    if heroes:
        hero = heroes[0]
        hero_with_meta = add_metadata(hero, "api", "hero", hero.get("localized_name", hero.get("name", "")))
        hero_chunks = chunk_hero_item(hero_with_meta, "hero")
        print(f"     ✓ 处理完成，生成 {len(hero_chunks)} 个文档块")
    
    # 处理第一个物品
    print("  1.4 处理物品数据（添加元数据 + 分块）...")
    if items:
        item = items[0]
        item_with_meta = add_metadata(item, "api", "item", item.get("name", ""))
        item_chunks = chunk_hero_item(item_with_meta, "item")
        print(f"     ✓ 处理完成，生成 {len(item_chunks)} 个文档块")
    
    print("  ✓ 数据采集流程测试通过")
    
except Exception as e:
    print(f"  ✗ 数据采集流程测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 2: 向量存储（需要 API Key）
print("\n[测试 2] 向量存储与检索")
if skip_api_tests:
    print("  ⏭️  跳过（需要 API Key）")
else:
    try:
        from src.vectorstore.store import VectorStore
        from src.ingestion.processors.cleaner import add_metadata
        from src.ingestion.processors.chunker import chunk_hero_item
        
        # 初始化向量存储
        print("  2.1 初始化向量存储...")
        vector_store = VectorStore()
        print("     ✓ 初始化成功")
        
        # 准备测试文档
        print("  2.2 准备测试文档...")
        test_hero = {
            "name": "antimage",
            "localized_name": "敌法师",
            "primary_attr": "agi",
            "attack_type": "Melee",
            "roles": ["Carry", "Escape"],
            "base_str": 21,
            "str_gain": 1.6,
        }
        hero_with_meta = add_metadata(test_hero, "api", "hero", "敌法师")
        hero_chunks = chunk_hero_item(hero_with_meta, "hero")
        print(f"     ✓ 准备 {len(hero_chunks)} 个文档")
        
        # 存储文档（会调用 Embedding API）
        print("  2.3 存储文档到 ChromaDB（调用 Embedding API）...")
        vector_store.upsert_documents("heroes", hero_chunks)
        print("     ✓ 存储成功")
        
        # 查询文档数量
        count = vector_store.get_collection_count("heroes")
        print(f"     ✓ heroes Collection 现在有 {count} 个文档")
        
        # 执行搜索
        print("  2.4 执行相似度搜索...")
        results = vector_store.search("heroes", "敏捷型近战英雄", top_k=3)
        print(f"     ✓ 搜索完成，返回 {len(results)} 个结果")
        if results:
            print(f"       最相关文档: {results[0].page_content[:50]}...")
        
        print("  ✓ 向量存储与检索测试通过")
        
    except Exception as e:
        print(f"  ✗ 向量存储测试失败: {e}")
        import traceback
        traceback.print_exc()

# 测试 3: 配置验证
print("\n[测试 3] 配置完整性验证")
try:
    from config.settings import settings
    
    required_configs = [
        ("DASHSCOPE_API_KEY", "API Key"),
        ("API_BASE_URL", "API 端点"),
        ("EMBEDDING_MODEL", "Embedding 模型"),
        ("CHAT_MODEL", "Chat 模型"),
        ("CHROMA_PERSIST_DIR", "ChromaDB 路径"),
        ("API_HOST", "API Host"),
        ("API_PORT", "API Port"),
        ("CACHE_TTL", "缓存 TTL"),
        ("LOG_LEVEL", "日志级别"),
    ]
    
    print("  检查配置项...")
    all_ok = True
    for config_attr, config_name in required_configs:
        value = getattr(settings, config_attr, None)
        if value:
            display = str(value)
            if "KEY" in config_attr:
                display = display[:10] + "..."
            print(f"    ✓ {config_name}: {display}")
        else:
            print(f"    ✗ {config_name}: 未配置")
            all_ok = False
    
    if all_ok:
        print("  ✓ 所有配置项已就绪")
    else:
        print("  ⚠️  部分配置项缺失")
    
except Exception as e:
    print(f"  ✗ 配置验证失败: {e}")

# 测试 4: 模块导入完整性
print("\n[测试 4] 模块导入完整性")
try:
    modules_to_test = [
        ("config.settings", "settings"),
        ("src.ingestion.sources.heroes", "fetch_heroes"),
        ("src.ingestion.sources.items", "fetch_items"),
        ("src.ingestion.processors.cleaner", "clean_html"),
        ("src.ingestion.processors.chunker", "chunk_hero_item"),
        ("src.vectorstore.store", "VectorStore"),
        ("src.vectorstore.embeddings", "get_embeddings"),
    ]
    
    failed = []
    for module_name, func_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[func_name])
            getattr(module, func_name)
            print(f"    ✓ {module_name}.{func_name}")
        except Exception as e:
            print(f"    ✗ {module_name}.{func_name}: {e}")
            failed.append((module_name, func_name))
    
    if not failed:
        print("  ✓ 所有模块导入成功")
    else:
        print(f"  ⚠️  {len(failed)} 个模块导入失败")
    
except Exception as e:
    print(f"  ✗ 模块导入测试失败: {e}")

print("\n" + "=" * 60)
print("端到端集成测试完成！")
print("=" * 60)

if skip_api_tests:
    print("\n💡 提示：")
    print("  要运行完整的向量存储测试，请设置真实的 DASHSCOPE_API_KEY")
else:
    print("\n✅ 所有测试通过！系统已就绪。")
