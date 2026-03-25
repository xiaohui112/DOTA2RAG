"""文档分块处理"""
import logging
from typing import List, Dict, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


def chunk_hero_item(entity_data: Dict[str, Any], category: str) -> List[Dict[str, Any]]:
    """
    英雄/物品数据分块：每个实体作为一个独立文档（不进一步分割）
    
    Args:
        entity_data: 实体数据字典
        category: 数据类别（hero/item）
        
    Returns:
        包含单个文档的列表
    """
    # 构建文档文本
    content_parts = []
    
    if category == "hero":
        content_parts.append(f"英雄名称: {entity_data.get('localized_name', entity_data.get('name', ''))}")
        content_parts.append(f"主要属性: {entity_data.get('primary_attr', '')}")
        content_parts.append(f"攻击类型: {entity_data.get('attack_type', '')}")
        content_parts.append(f"定位: {', '.join(entity_data.get('roles', []))}")
        content_parts.append(f"基础力量: {entity_data.get('base_str', 0)} (成长: {entity_data.get('str_gain', 0)})")
        content_parts.append(f"基础敏捷: {entity_data.get('base_agi', 0)} (成长: {entity_data.get('agi_gain', 0)})")
        content_parts.append(f"基础智力: {entity_data.get('base_int', 0)} (成长: {entity_data.get('int_gain', 0)})")
        content_parts.append(f"基础生命值: {entity_data.get('base_health', 0)}")
        content_parts.append(f"基础魔法值: {entity_data.get('base_mana', 0)}")
        content_parts.append(f"基础护甲: {entity_data.get('base_armor', 0)}")
        content_parts.append(f"基础魔抗: {entity_data.get('base_mr', 0)}")
        content_parts.append(f"攻击力: {entity_data.get('base_attack_min', 0)}-{entity_data.get('base_attack_max', 0)}")
        content_parts.append(f"攻击距离: {entity_data.get('attack_range', 0)}")
        content_parts.append(f"移动速度: {entity_data.get('move_speed', 0)}")
    elif category == "item":
        content_parts.append(f"物品名称: {entity_data.get('name', '')}")
        content_parts.append(f"价格: {entity_data.get('cost', 0)}")
        if entity_data.get('components'):
            content_parts.append(f"合成组件: {', '.join(map(str, entity_data.get('components', [])))}")
        if entity_data.get('attrib'):
            content_parts.append(f"属性加成: {entity_data.get('attrib', [])}")
        if entity_data.get('desc'):
            content_parts.append(f"描述: {entity_data.get('desc', '')}")
        if entity_data.get('notes'):
            content_parts.append(f"说明: {entity_data.get('notes', '')}")
    
    content = "\n".join(content_parts)
    
    # 返回单个文档，继承元数据
    doc = {
        "content": content,
        "metadata": entity_data.get("metadata", {}),
    }
    
    return [doc]


def chunk_patch_notes(patch_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    补丁说明分块：按类别（通用/英雄/物品）拆分为多个 chunk。

    如果英雄改动部分超过 1500 字符，进一步按英雄名拆分为独立 chunk。
    每个 chunk 包含 patch_version、change_category、timestamp 元数据。

    Args:
        patch_data: 补丁数据字典，包含:
            - name: 版本号
            - date: 发布日期
            - timestamp: 时间戳（可选）
            - general_changes: [str, ...]
            - hero_changes: [{"hero_name": str, "changes": [str]}, ...]
            - item_changes: [{"item_name": str, "changes": [str]}, ...]

    Returns:
        分块后的文档列表
    """
    chunks = []
    version = patch_data.get("name", patch_data.get("version", ""))
    date = patch_data.get("date", "")
    timestamp = patch_data.get("timestamp", 0)

    base_metadata = patch_data.get("metadata", {})

    # 1. 通用改动 chunk
    general_changes = patch_data.get("general_changes", [])
    if general_changes:
        content_lines = [
            f"Dota 2 版本 {version} — 通用改动",
            f"发布日期: {date}" if date else "",
            "",
        ]
        for change in general_changes:
            if isinstance(change, str):
                # general_changes 已包含格式化前缀（如 "- "、"【标题】"），直接添加
                content_lines.append(change)

        chunks.append({
            "content": "\n".join(line for line in content_lines if line is not None),
            "metadata": {
                **base_metadata,
                "source": "patch",
                "category": "patch",
                "entity_name": version,
                "patch_version": version,
                "patch_date": date,
                "patch_timestamp": timestamp,
                "change_category": "general",
            },
        })

    # 2. 英雄改动 chunk(s)
    hero_changes = patch_data.get("hero_changes", [])
    if hero_changes:
        # 先构建完整的英雄改动文本，判断是否需要拆分
        all_hero_text = _format_hero_changes(hero_changes, version, date)

        if len(all_hero_text) > 1500 and len(hero_changes) > 1:
            # 超过 1500 字符且有多个英雄 → 按英雄名拆分
            for hero_entry in hero_changes:
                hero_name = hero_entry.get("hero_name", "Unknown")
                hero_text = _format_single_hero_changes(hero_entry, version, date)
                chunks.append({
                    "content": hero_text,
                    "metadata": {
                        **base_metadata,
                        "source": "patch",
                        "category": "patch",
                        "entity_name": f"{version}_{hero_name}",
                        "patch_version": version,
                        "patch_date": date,
                        "patch_timestamp": timestamp,
                        "change_category": "hero",
                        "hero_name": hero_name,
                    },
                })
        else:
            # 未超阈值 → 单个 chunk
            chunks.append({
                "content": all_hero_text,
                "metadata": {
                    **base_metadata,
                    "source": "patch",
                    "category": "patch",
                    "entity_name": version,
                    "patch_version": version,
                    "patch_date": date,
                    "patch_timestamp": timestamp,
                    "change_category": "hero",
                },
            })

    # 3. 物品改动 chunk
    item_changes = patch_data.get("item_changes", [])
    if item_changes:
        content_lines = [
            f"Dota 2 版本 {version} — 物品改动",
            f"发布日期: {date}" if date else "",
            "",
        ]
        for item_entry in item_changes:
            if isinstance(item_entry, dict):
                item_name = item_entry.get("item_name", "Unknown")
                content_lines.append(f"### {item_name}")
                for change in item_entry.get("changes", []):
                    content_lines.append(f"- {change}")
                content_lines.append("")
            elif isinstance(item_entry, str):
                content_lines.append(f"- {item_entry}")

        chunks.append({
            "content": "\n".join(line for line in content_lines if line is not None),
            "metadata": {
                **base_metadata,
                "source": "patch",
                "category": "patch",
                "entity_name": version,
                "patch_version": version,
                "patch_date": date,
                "patch_timestamp": timestamp,
                "change_category": "item",
            },
        })

    # 4. 中立物品改动 chunk
    neutral_item_changes = patch_data.get("neutral_item_changes", [])
    if neutral_item_changes:
        content_lines = [
            f"Dota 2 版本 {version} — 中立物品改动",
            f"发布日期: {date}" if date else "",
            "",
        ]
        for ni_entry in neutral_item_changes:
            if isinstance(ni_entry, dict):
                item_name = ni_entry.get("item_name", "Unknown")
                content_lines.append(f"### {item_name}")
                for change in ni_entry.get("changes", []):
                    content_lines.append(f"- {change}")
                content_lines.append("")
            elif isinstance(ni_entry, str):
                content_lines.append(f"- {ni_entry}")

        chunks.append({
            "content": "\n".join(line for line in content_lines if line is not None),
            "metadata": {
                **base_metadata,
                "source": "patch",
                "category": "patch",
                "entity_name": version,
                "patch_version": version,
                "patch_date": date,
                "patch_timestamp": timestamp,
                "change_category": "neutral_item",
            },
        })

    # 如果没有任何详细内容，生成一个基础版本条目
    if not chunks:
        content = f"Dota 2 版本: {version}"
        if date:
            content += f"\n发布日期: {date}"
        chunks.append({
            "content": content,
            "metadata": {
                **base_metadata,
                "source": "patch",
                "category": "patch",
                "entity_name": version,
                "patch_version": version,
                "patch_date": date,
                "patch_timestamp": timestamp,
                "change_category": "summary",
            },
        })

    return chunks


def _format_hero_changes(
    hero_changes: List[Dict[str, Any]], version: str, date: str
) -> str:
    """格式化所有英雄改动为文本"""
    lines = [
        f"Dota 2 版本 {version} — 英雄改动",
        f"发布日期: {date}" if date else "",
        "",
    ]
    for hero_entry in hero_changes:
        if isinstance(hero_entry, dict):
            hero_name = hero_entry.get("hero_name", "Unknown")
            lines.append(f"### {hero_name}")
            for change in hero_entry.get("changes", []):
                lines.append(f"- {change}")
            lines.append("")
    return "\n".join(line for line in lines if line is not None)


def _format_single_hero_changes(
    hero_entry: Dict[str, Any], version: str, date: str
) -> str:
    """格式化单个英雄改动为文本"""
    hero_name = hero_entry.get("hero_name", "Unknown")
    lines = [
        f"Dota 2 版本 {version} — {hero_name} 改动",
        f"发布日期: {date}" if date else "",
        "",
    ]
    for change in hero_entry.get("changes", []):
        lines.append(f"- {change}")
    return "\n".join(line for line in lines if line is not None)


def chunk_wiki_article(article_data: Dict[str, Any], chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
    """
    Wiki 文章分块：递归字符分割
    
    Args:
        article_data: 文章数据字典
        chunk_size: 块大小（字符数）
        overlap: 重叠字符数
        
    Returns:
        分块后的文档列表
    """
    content = article_data.get("content", "")
    if not content:
        return []
    
    # 使用 LangChain 的递归字符分割器
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
    )
    
    # 分割文本
    chunks = text_splitter.split_text(content)
    
    # 为每个块添加元数据
    base_metadata = article_data.get("metadata", {})
    result = []
    for i, chunk_text in enumerate(chunks):
        chunk = {
            "content": chunk_text,
            "metadata": {
                **base_metadata,
                "chunk_index": i,
                "total_chunks": len(chunks),
            },
        }
        result.append(chunk)
    
    return result
