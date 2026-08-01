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
            json={
                "session_id": session_id, 
                "query": query, 
                "context": context,
                "cost_pressure": cost_pressure,
                "latency_pressure": latency_pressure
            },
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

    st.subheader("Stage 7: Recovery Index Demo")
    st.markdown("Did the LLM say it's missing context? Ask the **Recovery Index** to retrieve dropped chunks instantly.")
    
    missing_query = st.text_input("What is the LLM looking for?", placeholder="e.g. 'Authentication flow' or 'API keys'")
    
    if st.button("Recover Dropped Context", type="secondary"):
        with st.spinner("Checking ChromaDB/Memory store..."):
            rec_resp = requests.post(
                f"http://localhost:8000/recover?session_id={session_id}&missing_entity={missing_query}"
            )
            rec_data = rec_resp.json()
            
            if rec_data.get("found"):
                st.success("Target context recovered successfully! Ready to re-inject.")
                st.code(rec_data["results"]["documents"][0][0])
            else:
                st.warning("No dropped context matches that concept.")
