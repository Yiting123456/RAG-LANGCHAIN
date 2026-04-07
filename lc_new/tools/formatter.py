# tools/formatter.py
"""
结构化输出格式化器 — 将工具执行结果转化为结构化的诊断报告
"""
import json
from typing import List, Dict, Any, Optional


def extract_matched_tags_with_values(
    tool_steps: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    从 tool_steps 中提取 search_tags_local 的结果和对应的 get_tag_values

    输出结构：
    [
      {
        "id": 23,
        "tag": "03R02R02-E4.GAIN",
        "description": "Reject refiner spec. energy Control Proportion",
        "current_value": 1.5,
        "unit": "mg/L"
      },
      ...
    ]
    """
    matched_tags = {}  # {tag_id: tag_info}
    
    # 第一步：从 search_tags_local 得到候选 tag
    for step in tool_steps:
        if step.get("tool") == "search_tags_local":
            obs = step.get("observation", [])
            if isinstance(obs, list):
                for tag_item in obs:
                    tag_id = tag_item.get("id")
                    if tag_id:
                        matched_tags[tag_id] = {
                            "id": tag_id,
                            "tag": tag_item.get("tag", ""),
                            "description": tag_item.get("description", ""),
                            "type": tag_item.get("type", ""),
                            "score": tag_item.get("score", 0),
                            "current_value": None,
                            "unit": None,
                        }
    
    # 第二步：从 get_tag_values 得到实时值
    for step in tool_steps:
        if step.get("tool") == "get_tag_values":
            tag_id = step.get("args", {}).get("tag_id")
            obs = step.get("observation", {})
            
            if tag_id and tag_id in matched_tags:
                if isinstance(obs, dict):
                    # 尝试从返回的 JSON 中提取值
                    if "value" in obs:
                        matched_tags[tag_id]["current_value"] = obs["value"]
                    elif "values" in obs and isinstance(obs["values"], list) and len(obs["values"]) > 0:
                        matched_tags[tag_id]["current_value"] = obs["values"][0].get("v")
                    if "unit" in obs:
                        matched_tags[tag_id]["unit"] = obs["unit"]
    
    # 第三步：排序并返回
    result = list(matched_tags.values())
    result.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    return result


def extract_trend_and_anomaly(
    tool_steps: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    从 tool_steps 中提取 analyze_tag_anomaly 的结果和趋势

    输出结构：
    [
      {
        "tag_id": 23,
        "tag_name": "03R02R02-E4.GAIN",
        "status": "normal" | "abnormal" | "unknown",
        "latest_value": 1.5,
        "max_robust_z": 3.2,
        "reason": "description",
        "trend_points": [...]
      },
      ...
    ]
    """
    anomalies = {}  # {tag_id: anomaly_info}
    
    for step in tool_steps:
        if step.get("tool") == "analyze_tag_anomaly":
            tag_id = step.get("args", {}).get("tag_id")
            obs = step.get("observation", {})
            
            if tag_id:
                anomalies[tag_id] = {
                    "tag_id": tag_id,
                    "tag_name": "",
                    "status": obs.get("status", "unknown"),
                    "latest_value": obs.get("latest"),
                    "max_robust_z": obs.get("max_robust_z"),
                    "reason": obs.get("reason", ""),
                    "trend_points": obs.get("trend", []),  # 趋势数据
                }
    
    # 补充 tag 名称信息（从 search_tags_local 或其他地方）
    for step in tool_steps:
        if step.get("tool") == "search_tags_local":
            obs = step.get("observation", [])
            if isinstance(obs, list):
                for tag_item in obs:
                    tag_id = tag_item.get("id")
                    if tag_id and tag_id in anomalies:
                        anomalies[tag_id]["tag_name"] = tag_item.get("tag", "")
    
    result = list(anomalies.values())
    return result


def format_matched_tags_section(
    matched_tags: List[Dict[str, Any]]
) -> str:
    """
    格式化「本次匹配到的 Metris Tags 与实时值」部分
    """
    if not matched_tags:
        return "本次匹配到的 Metris Tags 与实时值：\n（无匹配结果）"
    
    lines = ["本次匹配到的 Metris Tags 与实时值：\n"]
    for idx, tag in enumerate(matched_tags, 1):
        tag_id = tag.get("id", "未知")
        tag_name = tag.get("tag", "未知")
        description = tag.get("description", "")
        current_value = tag.get("current_value")
        unit = tag.get("unit", "")
        
        value_str = f"{current_value} {unit}" if current_value is not None else "未获取到实时值"
        
        lines.append(f"{idx}. ID: {tag_id} | Tag: \"{tag_name}\" | 描述: \"{description}\" | 当前值: {value_str}")
    
    return "\n".join(lines)


def format_trend_section(
    trend_and_anomaly: List[Dict[str, Any]]
) -> str:
    """
    格式化「过去7天趋势/异常结论」部分
    """
    if not trend_and_anomaly:
        return "过去7天趋势/异常结论：\n（无数据）"
    
    lines = ["过去7天趋势/异常结论：\n"]
    for idx, item in enumerate(trend_and_anomaly, 1):
        tag_name = item.get("tag_name", "未知")
        status = item.get("status", "unknown")
        status_cn = {
            "abnormal": "异常",
            "normal": "正常",
            "unknown": "未知"
        }.get(status, "未知")
        
        latest = item.get("latest_value")
        max_z = item.get("max_robust_z")
        reason = item.get("reason", "")
        
        # 构造一条趋势描述
        if status == "abnormal":
            conclusion = f"异常，最大 robust-z 值为 {max_z}，表明存在明显偏离"
        elif status == "normal":
            conclusion = f"正常，无明显异常"
        else:
            conclusion = f"未知（可能数据不足），原因：{reason}"
        
        lines.append(f"{idx}. {tag_name}: {conclusion}")
    
    lines.append("\n（趋势图在 UI 中展示）")
    return "\n".join(lines)


def format_diagnostic_result(
    tool_steps: List[Dict[str, Any]],
    rag_result: Optional[Dict[str, Any]] = None,
    diagnosis_json: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    统一的结构化输出格式化函数

    输出：
    {
      "matched_tags": [...]，
      "trend_and_anomaly": [...],
      "formatted_output": {
        "matched_tags_section": "...",
        "trend_section": "...",
        "rag_summary": "...",
        "recommendations": "..."
      }
    }
    """
    matched_tags = extract_matched_tags_with_values(tool_steps)
    trend_and_anomaly = extract_trend_and_anomaly(tool_steps)
    
    # 格式化各个部分
    matched_tags_text = format_matched_tags_section(matched_tags)
    trend_text = format_trend_section(trend_and_anomaly)
    
    # RAG 总结部分
    rag_text = format_rag_summary(rag_result)
    
    # 建议部分
    recommendations_text = format_recommendations(diagnosis_json)
    
    return {
        "matched_tags": matched_tags,
        "trend_and_anomaly": trend_and_anomaly,
        "formatted_output": {
            "matched_tags_section": matched_tags_text,
            "trend_section": trend_text,
            "rag_summary": rag_text,
            "recommendations": recommendations_text,
        }
    }


def format_rag_summary(rag_result: Optional[Dict[str, Any]]) -> str:
    """
    格式化「资料库要点（RAG）」部分
    """
    if not rag_result:
        return "资料库要点（RAG）：\n（无相关资料）"
    
    lines = ["资料库要点（RAG）：\n"]
    
    qa_hits = rag_result.get("qa", [])
    process_hits = rag_result.get("process", [])
    
    all_hits = qa_hits + process_hits
    
    if not all_hits:
        lines.append("（无相关资料）")
    else:
        for idx, hit in enumerate(all_hits[:6], 1):  # 最多6条
            if isinstance(hit, dict):
                content = hit.get("content") or hit.get("text") or str(hit)
                if content:
                    # 简化显示
                    if len(content) > 100:
                        content = content[:100] + "..."
                    lines.append(f"{idx}. {content}")
    
    return "\n".join(lines)


def format_recommendations(diagnosis_json: Optional[Dict[str, Any]]) -> str:
    """
    格式化「建议」和「下一步」部分
    """
    if not diagnosis_json:
        return "建议与下一步：\n（无建议）"
    
    lines = ["建议与下一步：\n"]
    
    recommendations = diagnosis_json.get("recommendations", [])
    if isinstance(recommendations, list) and recommendations:
        lines.append("建议：")
        for idx, rec in enumerate(recommendations[:6], 1):
            if isinstance(rec, dict):
                text = rec.get("action") or rec.get("text") or str(rec)
            else:
                text = str(rec)
            if text:
                lines.append(f"{idx}. {text}")
    
    next_steps = diagnosis_json.get("next_steps", [])
    if isinstance(next_steps, list) and next_steps:
        lines.append("\n下一步：")
        for idx, step in enumerate(next_steps, 1):
            if isinstance(step, dict):
                text = step.get("action") or step.get("text") or str(step)
            else:
                text = str(step)
            if text:
                lines.append(f"{idx}. {text}")
    
    return "\n".join(lines)
