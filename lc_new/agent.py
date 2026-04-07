# lc_new/agent.py
import json
from typing import List, Dict, Any, Optional

import ollama
from tools.tools import TOOLS

LLM_MODEL = "qwen3:14b"


def plan_and_call_tools(
    user_query: str,
    trace: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Planner + Tool Calling（稳定版）
    返回结构（始终）:
    [
      {
        "tool": "...",
        "args": {...},
        "observation": {...}
      }
    ]
    """

    planner_prompt = f"""
你是 Andritz Metris 工厂数据诊断助手。

用户问题：
{user_query}

如果需要使用工厂数据，请返回 JSON 数组，例如：
[
  {{ "tool": "search_tags_local", "args": {{ "query": "温度" }} }},
  {{ "tool": "analyze_tag_anomaly", "args": {{ "tag_id": 123 }} }}
]

如果不需要任何工具，返回空数组：
[]

硬性工具链规则（非常重要）：
- 当问题涉及现场数据/异常/波动：必须先 search_tags_local 找到 tag id
- 对每个命中 tag id，必须调用：
  1) get_tag_values(tag_id) —— 获取实时值（必须有）
  2) analyze_tag_anomaly(tag_id) —— 基于过去7天趋势判断是否异常（必须有）
- 不再需要单独调用 get_trend_values（analyze_tag_anomaly 内部已包含）
- 若纯知识解释类问题，返回 []
- 只输出 JSON 数组，不要解释
"""

    if trace is not None:
        trace.append({
            "stage": "planner_prompt",
            "content": planner_prompt
        })

    # ---------- Step 1: Planner ----------
    resp = ollama.chat(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": planner_prompt}]
    )

    raw_content = resp["message"]["content"].strip()

    if trace is not None:
        trace.append({
            "stage": "planner_raw_output",
            "content": raw_content
        })

    try:
        plan = json.loads(raw_content)
        if not isinstance(plan, list):
            plan = []
    except Exception:
        plan = []

    if trace is not None:
        trace.append({
            "stage": "planner_parsed_plan",
            "plan": plan
        })

    # ---------- Step 2: Execute tools ----------
    results: List[Dict[str, Any]] = []

    for step in plan:
        tool_name = step.get("tool")
        args = step.get("args", {})

        matched_tool = next((t for t in TOOLS if t.name == tool_name), None)

        if not matched_tool:
            observation = {"error": f"tool '{tool_name}' not found"}
        else:
            try:
                observation = matched_tool.func(**args)
            except Exception as e:
                observation = {"error": str(e)}

        tool_step = {
            "tool": tool_name,
            "args": args,
            "observation": observation
        }
        results.append(tool_step)

        if trace is not None:
            trace.append({
                "stage": "tool_execution",
                "tool": tool_name,
                "args": args,
                "observation": observation
            })

    return results