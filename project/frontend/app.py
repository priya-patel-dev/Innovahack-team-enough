"""
ZipPrompt Dashboard - Premium Streamlit Console.
Allows users to paste code context, view live AST compression, monitor session diffs,
and trigger the in-memory recovery lookup loop.
"""
import os
import requests
import streamlit as st

# Set page config for wide layout and premium title
st.set_page_config(
    page_title="ZipPrompt Console",
    page_icon="🗜️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Premium Dark Mode Aesthetics
st.markdown("""
<style>
    .metric-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #38BDF8;
        margin-bottom: 4px;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .stage-badge {
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 8px;
    }
    .badge-selected {
        background-color: #064E3B;
        color: #34D399;
        border: 1px solid #059669;
    }
    .badge-dropped {
        background-color: #7F1D1D;
        color: #F87171;
        border: 1px solid #DC2626;
    }
</style>
""", unsafe_allow_html=True)

# Sample Code Loader Helper
SAMPLE_CODE = """class EnterpriseUserManagerProxyFactory:
    \"\"\"
    Very long class docstring that doesn't actually add any real semantic
    value but takes up dozens of tokens in a prompt window. We want the
    ZipPrompt compressor to rip this out or squish it heavily.
    \"\"\"

    def __init__(self):
        # Initialize variables
        self.user_data_cache = {}
        self.is_active = False
        self.last_login_timestamp = None

    def set_user_data_cache(self, cache):
        \"\"\" Setter for user_data_cache \"\"\"
        self.user_data_cache = cache
        return True

    def get_user_data_cache(self):
        \"\"\" Getter for user_data_cache \"\"\"
        return self.user_data_cache

    def set_is_active(self, active_state):
        \"\"\" Setter for is_active \"\"\"
        self.is_active = active_state
        return True

    def get_is_active(self):
        \"\"\" Getter for is_active \"\"\"
        return self.is_active

    def calculate_complex_user_metrics(self, user_id):
        \"\"\"
        Calculates complex metrics.
        This is the actual important function that answers queries about user metrics.
        \"\"\"
        # Step 1: Check if active
        if not self.get_is_active():
            return None
        
        # Step 2: Extract from cache
        if user_id in self.user_data_cache:
            base_score = self.user_data_cache[user_id].get("score", 0)
            
            # Step 3: Some arbitrary logic
            multiplier = 1.5 if base_score > 100 else 1.0
            
            return {
                "user_id": user_id,
                "final_score": base_score * multiplier,
                "status": "PROCESSED"
            }
        
        return None
"""

st.title("🗜️ ZipPrompt — Low-Resource LLM Context Compressor")
st.caption("Compiler-style context compression with structural parsing, query-aware routing, session-diff cache, and recovery index.")

# Session cache and sidebar
with st.sidebar:
    st.header("⚙️ Pipeline Configuration")
    
    session_id = st.text_input("Session Identifier", value="demo-session-1")
    
    st.subheader("Adaptive Budget Allocator")
    cost_pressure = st.slider("Cost Pressure (aggression)", 0.0, 1.0, 0.5, 
                              help="Higher cost pressure shrinks the allowed token budget.")
    latency_pressure = st.slider("Latency Pressure (aggression)", 0.0, 1.0, 0.4, 
                                help="Higher latency pressure forces shorter contexts to speed up time-to-first-token.")

    st.markdown("---")
    if st.button("📂 Load `messy_sample.py` Example", type="secondary"):
        st.session_state["context_input"] = SAMPLE_CODE
        st.session_state["query_input"] = "how does user metric scoring work?"

    st.markdown("### Differentiators")
    st.info(
        "1. **Structural representation**: AST parsing preserves code integrity.\n"
        "2. **Query-Aware**: Prioritizes nodes matching the query context.\n"
        "3. **Session Diff**: Only re-sends changed code blocks.\n"
        "4. **Recoverable**: Dropped blocks are indexed and pullable live."
    )

# Get values from session state if populated, else use defaults
context_default = st.session_state.get("context_input", "")
query_default = st.session_state.get("query_input", "")

# Inputs Section
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📝 Raw Prompt Context")
    context = st.text_area("Paste code repository files, logs, or prompt datasets here...", 
                           value=context_default, height=280)

with col_right:
    st.subheader("🔍 Active Search Query")
    query = st.text_area("What specific question are you asking the LLM about this context?", 
                         value=query_default, height=100, 
                         placeholder="e.g. How does user metric scoring work?")
    
    st.write("") # spacer
    compress_button = st.button("🚀 Compress Prompt Context", type="primary", use_container_width=True)

# Main Processing Loop
if compress_button:
    if not context or not query:
        st.error("Please provide both context and a query to execute the pipeline.")
    else:
        with st.spinner("Processing context through compiler pipeline..."):
            try:
                # Call backend `/compress` endpoint
                resp = requests.post(
                    "http://localhost:8000/compress",
                    json={
                        "session_id": session_id,
                        "query": query,
                        "context": context,
                        "cost_pressure": cost_pressure,
                        "latency_pressure": latency_pressure
                    },
                    timeout=10
                )
                data = resp.json()
                
                # Store data in session state for rendering sub-sections
                st.session_state["pipeline_data"] = data
                st.session_state["compression_executed"] = True
                
            except Exception as e:
                st.error(f"Failed to connect to FastAPI backend: {str(e)}")
                st.info("Make sure the backend is running at http://localhost:8000 (run `uvicorn main:app --reload` in project/backend)")

# Render Results
if st.session_state.get("compression_executed", False):
    data = st.session_state["pipeline_data"]
    
    st.markdown("---")
    st.subheader("📊 Live Pipeline Evaluation Metrics")
    
    # 4-Column metrics board
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{data['compression_ratio']*100:.1f}%</div>
            <div class="metric-label">Token Reduction</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">${data['original_tokens'] / 1000 * 0.003:.5f} ➔ ${data['compressed_tokens'] / 1000 * 0.003:.5f}</div>
            <div class="metric-label">Prompt Cost (Sonnet)</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">+{data['latency_speedup_pct']*100:.1f}%</div>
            <div class="metric-label">Inference Speedup</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{data['reasoning_retention_score']*100:.1f}%</div>
            <div class="metric-label">Reasoning Retention</div>
        </div>
        """, unsafe_allow_html=True)

    # Pipeline Visualizer showing which parts were selected/dropped
    st.write("")
    st.subheader("⛓️ AST Node Allocation")
    
    sel_cols = st.columns(2)
    with sel_cols[0]:
        st.markdown("**🟢 Selected & Cleaned Nodes (Sent to target LLM):**")
        for node in data["selected_nodes"]:
            st.markdown(f"<span class='stage-badge badge-selected'>{node}</span>", unsafe_allowed_html=True)
        if not data["selected_nodes"]:
            st.write("None")
            
    with sel_cols[1]:
        st.markdown("**🔴 Dropped & Stored Nodes (Index-recoverable):**")
        for node in data["dropped_nodes"]:
            st.markdown(f"<span class='stage-badge badge-dropped'>{node}</span>", unsafe_allowed_html=True)
        if not data["dropped_nodes"]:
            st.write("None (All nodes fit within budget)")

    # Side by side code view
    st.write("")
    view_col1, view_col2 = st.columns(2)
    with view_col1:
        st.subheader("Original Context")
        st.code(context, language="python")
    with view_col2:
        st.subheader("Compressed Prompt (Cleaned & Minimal)")
        st.code(data["compressed_prompt"], language="python")

# Stage 7 Recovery Index Panel
st.markdown("---")
st.subheader("🔄 Stage 7: Recovery Store Lookup")
st.caption("Simulates the target LLM signaling it is missing information. Enter a keyword to retrieve it from the index live.")

rec_col1, rec_col2 = st.columns([3, 1])
with rec_col1:
    missing_key = st.text_input("Enter missing entity / concept keyword", 
                               placeholder="e.g. EnterpriseUserManagerProxyFactory or constructor",
                               key="missing_key_input")
with rec_col2:
    st.write("") # spacer
    recover_button = st.button("🔍 Pull from Recovery Store", use_container_width=True)

if recover_button:
    if not missing_key:
        st.warning("Please enter a search keyword.")
    else:
        with st.spinner("Searching in-memory index..."):
            try:
                rec_resp = requests.post(
                    f"http://localhost:8000/recover?session_id={session_id}&missing_entity={missing_key}",
                    timeout=10
                )
                rec_data = rec_resp.json()
                
                if rec_data.get("found", False):
                    st.success(f"Successfully retrieved matching node from recovery store!")
                    
                    results = rec_data["results"]
                    # Unpack chromadb-like nested structures
                    for doc_idx in range(len(results["documents"][0])):
                        node_name = results["metadatas"][0][doc_idx]["name"]
                        node_id = results["ids"][0][doc_idx]
                        node_body = results["documents"][0][doc_idx]
                        
                        st.info(f"**Recovered Node:** {node_name} (ID: {node_id})")
                        st.code(node_body, language="python")
                else:
                    st.warning("No matching nodes found in the recovery store for this session.")
            except Exception as e:
                st.error(f"Error querying recovery store: {str(e)}")
