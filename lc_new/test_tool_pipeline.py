# test_tool_pipeline.py
# ============================
# 用于验证：
# 用户输入 → tag 描述匹配 → tag id → 工具调用链
# ============================

import json
from agent import plan_and_call_tools


def pretty_print(title, obj):
    print("\n" + "=" * 80)
    print(title)
    print("-" * 80)
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    print("=" * 80)


def run_test_case(user_query: str):
    print("\n\n🧪 测试输入：")
    print(user_query)

    tool_steps = plan_and_call_tools(user_query)

    if not tool_steps:
        print("⚠️  Planner 判断：不需要任何工具")
        return

    pretty_print("🧠 Tool Calling 结果（完整 Trace）", tool_steps)

    # ✅ 验证点 1：是否命中了 tag
    hit_tags = []
    for step in tool_steps:
        obs = step.get("observation", {})
        if isinstance(obs, list):
            for item in obs:
                if isinstance(item, dict) and "id" in item:
                    hit_tags.append(item["id"])
        if isinstance(obs, dict) and "tag_id" in obs:
            hit_tags.append(obs["tag_id"])

    if hit_tags:
        print(f"\n✅ 命中的 Tag ID：{sorted(set(hit_tags))}")
    else:
        print("\n❌ 未命中任何 Tag（需要检查 piptags_min.json 或描述匹配）")


if __name__ == "__main__":

    TEST_CASES = [
        # ✅ 应该触发 search_tags_local
        "高浓压力最近有没有异常波动？",

        # ✅ 应该命中 description 而不是 tag 名称
        "成浆塔出口浓度有点不稳定",

        # ✅ 同时触发 历史 + 异常
        "主线流量过去一周是否异常",

        # ✅ 模糊描述，验证相似度搜索
        "真空系统有点怪，数值抖动",

        # ✅ 边界测试：不应调用工具
        "请解释一下高浓系统的作用"
    ]

    for q in TEST_CASES:
        run_test_case(q)
