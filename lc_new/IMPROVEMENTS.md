# 系统优化总结

## 优化目标
根据用户需求，优化 Andritz Metris Agent 诊断系统的工具调用链和输出格式，确保：
1. 对于用户query，先匹配piptags_min中的描述，返回多个可能的tag
2. 返回的每个id都自动调用get_tag_values和analyze_tag_anomaly
3. 输出按结构化格式组织（Tags、趋势、RAG资料库、建议）

---

## 核心改进

### 1. **agent.py** - 智能工具链自动扩展
**问题**: 原系统仅执行规划的工具，需要手动指定每个tag的后续工具调用。

**改进**:
- 实现自动扩展机制：当`search_tags_local`返回多个tag时，系统自动为每个tag_id调用：
  - `get_tag_values` - 获取实时值
  - `analyze_tag_anomaly` - 分析异常趋势
- 简化LLM规划提示，不需要在plan中指定这些工具，系统自动执行

**关键代码**:
```python
# 在执行每个tool后，如果是search_tags_local，自动调用后续工具
if tool_name == "search_tags_local" and isinstance(observation, list):
    for tag_item in observation:
        # 自动调用 get_tag_values 和 analyze_tag_anomaly
```

---

### 2. **tools/formatter.py** - 新增结构化格式化工具
**功能**: 将工具执行结果转化为结构化的诊断报告。

**主要函数**:

#### `extract_matched_tags_with_values(tool_steps)`
从工具步骤中提取匹配的Tags和实时值。
```python
输出:
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
```

#### `extract_trend_and_anomaly(tool_steps)`
从工具步骤中提取趋势数据和异常结论。
```python
输出:
[
  {
    "tag_id": 23,
    "tag_name": "03R02R02-E4.GAIN",
    "status": "normal|abnormal|unknown",
    "latest_value": 1.5,
    "max_robust_z": 3.2,
    "trend_points": [...]  # 用于绘制趋势图
  },
  ...
]
```

#### `format_diagnostic_result(tool_steps, rag_result, diagnosis_json)`
统一的结构化输出，包含所有部分。

**输出结构**:
```python
{
  "matched_tags": [...],
  "trend_and_anomaly": [...],
  "formatted_output": {
    "matched_tags_section": "本次匹配到的 Metris Tags...",
    "trend_section": "过去7天趋势/异常结论...",
    "rag_summary": "资料库要点（RAG）...",
    "recommendations": "建议与下一步..."
  }
}
```

---

### 3. **main.py** - 整合新的格式化流程
**改进**:
- 导入新的formatter模块
- 在`diagnose()`函数中集成`format_diagnostic_result()`
  - 生成结构化输出部分：`matched_tags`、`trend_analysis`
  - 将结构化结果添加到诊断JSON中
- 改进`render_report()`函数
  - 使用结构化格式化结果
  - 当LLM调用失败时，回退到格式化输出

**关键步骤**:
```python
# Step 3.7: 结构化格式化
formatted_result = format_diagnostic_result(
    tool_steps=tool_steps,
    rag_result=rag_result,
    diagnosis_json=diagnosis
)

# 添加到诊断结果
diagnosis["structured_output"] = formatted_result.get("formatted_output", {})
diagnosis["matched_tags"] = formatted_result.get("matched_tags", [])
diagnosis["trend_analysis"] = formatted_result.get("trend_and_anomaly", [])
```

---

### 4. **tools/anomaly.py** - 增强统计信息
**改进**:
- 添加详细的统计信息（均值、中值、标准差、最小/最大值）
- 改进异常信息返回结构
- 支持向量化输出

**输出结构**:
```python
{
    "status": "normal|abnormal|unknown",
    "latest": 最新值,
    "max_robust_z": 最大z值,
    "statistics": {
        "mean": 均值,
        "median": 中值,
        "std": 标准差,
        "min": 最小值,
        "max": 最大值,
        "count": 数据点数
    }
}
```

---

### 5. **tools/tools.py** - 改进analyze_tag_anomaly
**改进**:
- 正确处理趋势数据提取（支持多种格式）
- 确保趋势数据（trend_points）在返回中包含
- 用于趋势图绘制和数据追溯

---

### 6. **tools/metris_api.py** - 清理和文档化
**改进**:
- 添加详细的文档说明
- 移除测试代码（print语句）
- 明确返回格式

---

### 7. **ui_streamlit.py** - 增强UI展示
**改进**:
- 新增"显示结构化诊断结果"切换选项（默认启用）
- 展示匹配到的Tags及其实时值
- 展示趋势图和异常结论
- 改进趋势数据的可视化
- 保持自然语言报告作为补充展示

**UI结构**:
```
匹配到的 Metris Tags 与实时值 (可展开)
  - ID | Tag | Description | 当前值

过去7天趋势/异常结论 (可展开)
  - Tag名称: 状态 (正常/异常)
  - 最新值、最大Z值
  - 趋势图表

诊断报告（自然语言）
  - LLM生成的自然语言说明

完整JSON (可选)
  - 完整的诊断数据

Debug Trace (可选)
  - 执行过程追溯
```

---

## 输出格式示例

### 本次匹配到的 Metris Tags 与实时值
```
1. ID: 23 | Tag: "03R02R02-E4.GAIN" | 描述: "Reject refiner spec. energy Control Proportion" | 当前值: 1.5 mg/L
2. ID: 30 | Tag: "03R02R02-F1.PV" | 描述: "Reject refiner A flow Process Values" | 当前值: 12.3 m³/h
...
```

### 过去7天趋势/异常结论
```
1. 03R02R02-E4.GAIN: 异常，最大 robust-z 值为 3.8，表明存在明显偏离
2. 03R02R02-F1.PV: 正常，无明显异常
...
（趋势图在 UI 中展示）
```

### 资料库要点（RAG）
```
1. 过程描述表明，高浓漂白塔中双氧水的残余量约为 20%。
2. 过程描述中提到，高浓漂白塔温度控制在 2-3°C。
...
```

### 建议与下一步
```
建议：
1. 检查温度控制系统，确保温度稳定在允许范围内。
2. 监测金属离子浓度，并及时调整工艺参数。
...

下一步：
1. 需要获取 H2O2消耗的实时值，以确定趋势的持续时间和幅度。
2. 需要分析工艺参数和设备运行数据...
```

---

## 数据流改进

### 原流程
```
User Query 
  → Planner (规划工具)
    → search_tags_local (手动指定)
    → get_tag_values (手动指定)
    → analyze_tag_anomaly (手动指定)
  → RAG搜索
  → LLM诊断
  → 自然语言报告
```

### 优化后流程
```
User Query
  → Planner (简化，仅需search_tags_local)
    → search_tags_local (自动返回多个tags)
      → [自动扩展] get_tag_values (对每个tag_id)
      → [自动扩展] analyze_tag_anomaly (对每个tag_id)
  → [优化] 结构化格式化 (extract & format)
    ├─ 匹配Tags与实时值
    ├─ 趋势与异常结论
    ├─ RAG资料库要点
    └─ 建议与下一步
  → RAG搜索
  → LLM诊断
  → 自然语言报告 (基于结构化输出增强)
  → [改进UI] 分层展示 (结构化 + 自然语言)
```

---

## 使用注意

1. **配置路径**: 确保`piptags_min.json`、`Q&A.json`、`process.json`的路径正确
2. **LLM模型**: 仍使用 `gemma:latest`，确保Ollama服务运行
3. **METRIS API**: 确保环境变量配置正确（METRIS_URI, METRIS_USERNAME, METRIS_PASSWORD）
4. **Streamlit UI**: 运行 `streamlit run ui_streamlit.py` 启动

---

## 测试建议

1. 测试search_tags_local返回多个tags时的自动工具扩展
2. 验证趋势图数据的正确性
3. 测试UI中不同展示选项的效果
4. 验证结构化输出中各字段的准确性
5. 测试LLM报告生成的效果

---

## 后续优化方向

1. 支持多张趋势图并行展示
2. 添加趋势预测功能
3. 实现更智能的Tags自动排序
4. 添加异常原因的自动识别
5. 支持多语言输出
