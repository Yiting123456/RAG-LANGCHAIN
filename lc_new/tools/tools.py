# tools/tools.py
from langchain_core.tools import Tool   # 这里只是数据结构，不会触发 torch

from tools.tag_search import search_tags_local
from tools.metris_api import get_tag_values, get_trend_values
from tools.anomaly import analyze_series_anomaly


def analyze_tag_anomaly(tag_id: int):
    """
    对单个 tag 做异常分析
    """
    trend = get_trend_values(tag_id)
    values = []

    for p in trend:
        v = p.get("v")
        if isinstance(v, (int, float)):
            values.append(v)

    result = analyze_series_anomaly(values)
    result["tag_id"] = tag_id
    return result


# ✅ ✅ ✅ 关键：必须显式定义 TOOLS
TOOLS = [
    Tool(
        name="search_tags_local",
        func=search_tags_local,
        description="根据描述模糊搜索可能相关的 Metris tag"
    ),
    Tool(
        name="get_tag_values",
        func=get_tag_values,
        description="查询指定 tag 的实时值"
    ),
    Tool(
        name="get_trend_values",
        func=get_trend_values,
        description="查询指定 tag 的历史趋势"
    ),
    Tool(
        name="analyze_tag_anomaly",
        func=analyze_tag_anomaly,
        description="基于历史数据分析 tag 是否异常"
    ),
]