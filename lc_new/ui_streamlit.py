import streamlit as st

from main import diagnose


# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="Andritz Metris Agent",
    layout="wide"
)

st.title("🧠 Andritz Metris Agent")
st.caption("工业级 Planner + Tool Calling + RAG + 可解释诊断（含自然语言报告）")


# ============================================================
# 侧边栏：显示控制
# ============================================================
with st.sidebar:
    st.header("显示设置")
    show_json = st.checkbox("显示结构化 JSON", value=False)
    show_trace = st.checkbox("显示 Debug Trace", value=False)
    include_trace_in_backend = st.checkbox("后端生成 Trace（影响耗时）", value=True)
    st.divider()
    st.write("提示：默认优先展示自然语言报告，JSON/Trace 适合开发调试时打开。")


# ============================================================
# 会话状态
# ============================================================
if "messages" not in st.session_state:
    st.session_state.messages = []


# ============================================================
# 历史对话展示
# ============================================================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            # 自然语言报告优先
            st.markdown("### ✅ 诊断结论（自然语言）")
            st.markdown(msg["content"].get("report", "（无自然语言报告）"))

            # 可选：结构化 JSON
            if show_json:
                with st.expander("📦 结构化诊断结果（JSON）", expanded=False):
                    st.json(msg["content"])

            # 可选：Trace
            if show_trace:
                with st.expander("🧩 Agent 执行全过程（Debug Trace）", expanded=False):
                    for step in msg["content"].get("trace", []):
                        st.markdown(f"#### 🔹 {step.get('stage')}")
                        st.json(step)

        else:
            st.markdown(msg["content"])


# ============================================================
# 用户输入
# ============================================================
user_input = st.chat_input(
    "请输入工厂/工艺问题，例如：高浓磨温度为什么会上升？"
)

if user_input:
    # 保存用户输入
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    # 调用诊断
    with st.chat_message("assistant"):
        with st.spinner("🧠 Agent 正在分析（Planner → Tool → RAG → Diagnosis → Report）…"):
            result = diagnose(user_input, include_trace=include_trace_in_backend)

        # 自然语言报告
        st.markdown("### ✅ 诊断结论（自然语言）")
        st.markdown(result.get("report", "（无自然语言报告）"))

        # 可选：结构化 JSON
        if show_json:
            with st.expander("📦 结构化诊断结果（JSON）", expanded=False):
                st.json(result)

        # 可选：Debug Trace
        if show_trace:
            with st.expander("🧩 Agent 执行全过程（Debug Trace）", expanded=False):
                for step in result.get("trace", []):
                    st.markdown(f"#### 🔹 {step.get('stage')}")
                    st.json(step)

    # 保存 assistant 结果
    st.session_state.messages.append({
        "role": "assistant",
        "content": result
    })