# tools/tag_search.py
import os
import json
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional

# ============================================================
# Tag JSON 路径（可通过 .env 覆盖）
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TAG_JSON_PATH = os.getenv(
    "TAG_JSON_PATH",
    r"C:\Users\Administrator\yt\lc\piptags_min.json"
)

if not os.path.isabs(TAG_JSON_PATH):
    TAG_JSON_PATH = os.path.join(BASE_DIR, TAG_JSON_PATH)

# ============================================================
# 内存缓存（避免重复加载）
# ============================================================
_TAG_INDEX: Optional[List[Dict[str, str]]] = None


# ============================================================
# 相似度函数（简单、稳定、工业够用）
# ============================================================
def _sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ============================================================
# 加载 Tag JSON
# 期望结构：
# {
#   "1": {"Tag": "...", "Description": "..."},
#   "2": {"Tag": "...", "Description": "..."}
# }
# ============================================================
def _load_tag_json() -> List[Dict[str, str]]:
    global _TAG_INDEX

    if _TAG_INDEX is not None:
        return _TAG_INDEX

    if not os.path.exists(TAG_JSON_PATH):
        _TAG_INDEX = []
        return _TAG_INDEX

    try:
        with open(TAG_JSON_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)

        items: List[Dict[str, str]] = []

        if isinstance(raw, dict):
            for tag_id, obj in raw.items():
                if not isinstance(obj, dict):
                    continue

                tag_name = (obj.get("Tag") or "").strip()
                desc = (obj.get("Description") or "").strip()
                tag_type = (obj.get("Type") or "").strip()

                if str(tag_id).isdigit() and tag_name:
                    items.append({
                        "id": int(tag_id),
                        "tag": tag_name,
                        "description": desc,
                        "type": tag_type
                    })

        _TAG_INDEX = items
        return items

    except Exception:
        _TAG_INDEX = []
        return _TAG_INDEX


# ============================================================
# ✅ 核心函数：本地 Tag 语义搜索
# ============================================================
def search_tags_local(
    query: str,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    在本地 Tag JSON 中搜索可能相关的 Tag

    输入：
        query: 用户描述 / 问题
        top_k: 返回数量

    输出：
        [
          {
            "id": 123,
            "tag": "XXX",
            "description": "...",
            "type": "...",
            "score": 0.78
          }
        ]
    """

    if not query or not query.strip():
        return []

    query = query.strip()
    tags = _load_tag_json()

    scored: List[tuple] = []

    for t in tags:
        score = max(
            _sim(query, t.get("tag", "")),
            _sim(query, t.get("description", ""))
        )
        if score > 0:
            scored.append((score, t))

    scored.sort(key=lambda x: x[0], reverse=True)

    results: List[Dict[str, Any]] = []
    for score, t in scored[:top_k]:
        results.append({
            "id": t["id"],
            "tag": t["tag"],
            "description": t["description"],
            "type": t.get("type", ""),
            "score": round(score, 4)
        })

    return results