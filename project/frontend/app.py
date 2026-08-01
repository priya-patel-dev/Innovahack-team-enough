"""
ZipPrompt dashboard - Streamlit scaffold.

Run with: streamlit run frontend/app.py
Expects the FastAPI backend running at http://localhost:8000
"""
import requests
import streamlit as st

st.set_page_config(page_title="ZipPrompt", layout="wide")
st.title("🗜️ ZipPrompt — Ultra-Low Resource LLM Context Compression")

with st.sidebar:
    st.header("Controls")
    session_id = st.text_input("Session ID", value="demo-session-1")
    cost_pressure = st.slider("Cost pressure (adaptive budget)", 0.0, 1.0, 0.5)
    latency_pressure = st.slider("Latency pressure (adaptive budget)", 0.0, 1.0, 0.5)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Raw Context (code / logs)")
    context = st.text_area("Paste context here", height=300)

with col2:
    st.subheader("Query")
    query = st.text_area("What are you asking about this context?", height=100)

if st.button("Compress", type="primary"):
    with st.spinner("Running pipeline..."):
        resp = requests.post(
            "http://localhost:8000/compress",
            json={"session_id": session_id, "query": query, "context": context},
        )
        data = resp.json()

    st.subheader("Results")
    m1, m2, m3 = st.columns(3)
    m1.metric("Compression Ratio", f"{data['compression_ratio']*100:.1f}%")
    m2.metric("Original Tokens", data["original_tokens"])
    m3.metric("Compressed Tokens", data["compressed_tokens"])

    st.subheader("Compressed Prompt")
    st.code(data["compressed_prompt"])

    # TODO: wire up eval_harness results here once /compress is live -
    # cost reduction, reasoning retention, latency speedup panels.

st.divider()
st.caption(
    "Next: wire recovery panel (Stage 7) - show a dropped chunk being "
    "retrieved live when the LLM answer signals missing info."
)
