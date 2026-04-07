import json
from typing import Dict, Any, List, Optional, Set

import ollama

from agent import plan_and_call_tools
from tools.alarm import should_trigger_alarm, trigger_alarm
from tools.rag import build_qa_index, build_process_index, rag_search
from prompts.diagnosis_prompt import DIAGNOSIS_PROMPT

LLM_MODEL = "qwen3:14b"


# ============================================================
# LLM 调用（原生 Ollama）
# ============================================================
def llm_chat(system_prompt: str, user_prompt: str) -> str:
    resp = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    return resp["message"]["content"]


# ============================================================
# RAG 向量预加载
# ============================================================
QA_VECTORS = build_qa_index(
    r"C:\Users\Administrator\yt\lc_new\data\Q&A.json"
)
PROCESS_VECTORS = build_process_index(
    r"C:\Users\Administrator\yt\lc_new\data\process.json"
)


# ============================================================
# 可信度评分
# ============================================================
def calc_confidence(tag_count: int, has_abnormal: bool, rag_hits: int) -> float:
    score = 0.0
    if tag_count >= 2:
        score += 0.4
    elif tag_count == 1:
        score += 0.2

    if has_abnormal:
        score += 0.3

    if rag_hits > 0:
        score += 0.3

    return round(min(score, 1.0), 2)


# ============================================================
# 自然语言渲染 Prompt（把 JSON 诊断转成报告）
# ============================================================
REPORT_PROMPT = """你是一名资深造纸/制浆工艺与自动化工程师助手。
把输入信息改写为现场工程师可直接使用的诊断说明。

硬性要求：
- 只输出自然语言（不要JSON、不要代码块）
- 不得捏造输入中不存在的任何数值/结论
- 实时值必须来自 tool_steps 中 get_tag_values 的返回；若缺失必须写“未获取到实时值”
- 过去7天判断必须来自 analyze_tag_anomaly 的返回；若缺失必须写“缺少过去7天异常判断”
- RAG 只提炼要点，不贴原文大段
- 语言：中文；风格：专业、克制、可执行

必须按以下结构输出（用自然语言段落分隔即可）：
1）本次匹配到的 Metris Tag 与实时值：
- 写明匹配到哪些 Tag（名称/描述 + id）
- 对每个 Tag 写当前实时值（不编单位）

2）过去7天趋势/异常结论：
- 对每个 Tag 写 abnormal/normal/unknown，并引用返回里的证据字段（如 max_robust_z、n_points、min/max/mean、latest 等）

3）资料库要点（RAG）：
- 列出最相关的要点（全部输出，来自 qa/process）

4）建议（可执行）：
- 3~6条工程动作建议，按优先级排列
- 若信息不足，明确下一步需要补采哪些 Tag/现象/日志
"""


def render_report(
    user_query: str,
    diagnosis_json: Dict[str, Any],
    tool_steps: Optional[List[Dict[str, Any]]] = None,
    rag_result: Optional[Dict[str, Any]] = None,
) -> str:
    """
    将结构化诊断结果再次调用 LLM，渲染为自然语言报告（非 JSON）。
    """
    payload = {
        "user_query": user_query,
        "diagnosis": diagnosis_json,
        "tool_steps": tool_steps or [],
        "rag": rag_result or {}
    }

    user_prompt = (
        "请把下面信息改写成自然语言诊断报告（仅自然语言，不要JSON）：\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    return llm_chat(system_prompt=REPORT_PROMPT, user_prompt=user_prompt)


# ============================================================
# 工业诊断主流程（✅核心）
# ============================================================
def diagnose(user_query: str, include_trace: bool = True) -> Dict[str, Any]:
    trace: List[Dict[str, Any]] = []

    # ---------- Step 1: Planner + Tool Calling ----------
    tool_steps = plan_and_call_tools(user_query, trace=trace)

    used_tags: Set[Any] = set()
    has_abnormal = False

    for step in tool_steps:
        obs = step.get("observation", {})
        if isinstance(obs, dict):
            if "tag_id" in obs:
                used_tags.add(obs["tag_id"])
            if obs.get("status") == "abnormal":
                has_abnormal = True

    trace.append({
        "stage": "tool_summary",
        "tool_steps": tool_steps
    })

    # ---------- Step 2: RAG ----------
    rag_query = f"""
用户问题：
{user_query}

工具调用结果：
{json.dumps(tool_steps, ensure_ascii=False)}
"""

    rag_result = rag_search(
        query=rag_query,
        qa_vectors=QA_VECTORS,
        process_vectors=PROCESS_VECTORS,
        top_k_qa=1,
        top_k_process=2
    )

    trace.append({
        "stage": "rag",
        "query": rag_query,
        "result": rag_result
    })

    # ---------- Step 3: Diagnosis (JSON) ----------
    diagnosis_input = f"""
【用户问题】
{user_query}

【工具数据】
{json.dumps(tool_steps, ensure_ascii=False, indent=2)}

【知识库内容】
{json.dumps(rag_result, ensure_ascii=False, indent=2)}
"""

    raw_output = llm_chat(
        system_prompt=DIAGNOSIS_PROMPT,
        user_prompt=diagnosis_input
    )

    trace.append({
        "stage": "diagnosis_llm",
        "prompt": diagnosis_input,
        "raw_output": raw_output
    })

    try:
        diagnosis = json.loads(raw_output)
        if not isinstance(diagnosis, dict):
            raise ValueError("LLM output is not a JSON object.")
    except Exception:
        # JSON 解析失败 fallback
        diagnosis = {
            "summary": raw_output,
            "anomalies": [],
            "possible_causes": [],
            "recommendations": []
        }

    # ---------- Step 3.5: confidence ----------
    diagnosis["confidence"] = calc_confidence(
        tag_count=len(used_tags),
        has_abnormal=has_abnormal,
        rag_hits=len(rag_result.get("qa", [])) + len(rag_result.get("process", []))
    )

    # ---------- Step 4: Render Natural Language Report ----------
    # 用“结构化诊断 + 工具 + RAG”二次渲染为自然语言报告
    try:
        report = render_report(
            user_query=user_query,
            diagnosis_json=diagnosis,
            tool_steps=tool_steps,
            rag_result=rag_result
        )
    except Exception as e:
        report = f"自然语言报告生成失败：{type(e).__name__}: {e}"

    diagnosis["report"] = report

    trace.append({
        "stage": "report_llm",
        "report": report
    })

    # ---------- attach trace ----------
    if include_trace:
        diagnosis["trace"] = trace
    else:
        diagnosis["trace"] = []

    # ---------- alarm ----------
    if should_trigger_alarm(diagnosis):
        trigger_alarm(diagnosis)

    return diagnosis


# ============================================================
# CLI 入口
# ============================================================
if __name__ == "__main__":
    print("✅ Andritz Metris 工厂诊断 Agent 已启动")

    while True:
        user_input = input("\n请输入问题（exit 退出）：").strip()
        if user_input.lower() in ("exit", "quit"):
            break

        try:
            result = diagnose(user_input, include_trace=True)
            print("\n================ 自然语言报告 ================")
            print(result.get("report", "（无报告）"))
            print("\n================ 结构化诊断（JSON） ================")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print("================================================")
        except Exception as e:
            print("\n❌ 诊断过程中发生异常：")
            print(type(e).__name__, ":", e)
