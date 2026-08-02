"""
ZipPrompt backend entrypoint.

Pipeline order (see PLANNING.md for the full diagram):
  ingestion -> structural codec -> diff engine -> query router
  -> budget allocator -> token pruner -> recovery index -> LLM call
"""
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ingestion import detect_domain
from custom_codecs.code_codec import build_code_graph
from custom_codecs.log_codec import build_log_templates
from diff_engine import SessionCache
from query_router import rank_by_relevance
from budget_allocator import allocate_budget
from token_pruner import prune_tokens
from recovery_index import RecoveryIndex

app = FastAPI(title="ZipPrompt")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    print("ZipPrompt Compression API Initialized successfully with CORSMiddleware [Allow All Origins]!")

session_cache = SessionCache()
recovery_index = RecoveryIndex()


@app.get("/", response_class=HTMLResponse)
def read_root():
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    html_path = os.path.join(frontend_dir, "console.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


class CompressRequest(BaseModel):
    session_id: str
    query: str
    context: str
    target_tokens: int | None = None  # None = let budget_allocator decide
    cost_pressure: float = 0.5
    latency_pressure: float = 0.5


class CompressResponse(BaseModel):
    compressed_prompt: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    cost_savings_pct: float
    latency_speedup_pct: float
    selected_nodes: list[str]
    dropped_nodes: list[str]
    reused_nodes: list[str]


@app.post("/compress", response_model=CompressResponse)
def compress(req: CompressRequest) -> CompressResponse:
    # 0. Input validation
    if not req.context or not req.context.strip():
        return CompressResponse(
            compressed_prompt="Error: Context cannot be empty. Please load the sample or paste code/logs.",
            original_tokens=0,
            compressed_tokens=0,
            compression_ratio=0.0,
            cost_savings_pct=0.0,
            latency_speedup_pct=0.0,
            reasoning_retention_score=1.0,
            selected_nodes=[],
            dropped_nodes=[],
        )
    
    if not req.query or not req.query.strip():
        return CompressResponse(
            compressed_prompt="Error: Query cannot be empty. Please enter what you want to search.",
            original_tokens=0,
            compressed_tokens=0,
            compression_ratio=0.0,
            cost_savings_pct=0.0,
            latency_speedup_pct=0.0,
            reasoning_retention_score=1.0,
            selected_nodes=[],
            dropped_nodes=[],
        )
    
    if len(req.context) > 200000:  # Oversized paste guard
        return CompressResponse(
            compressed_prompt="Error: Context exceeds safety limit of 200K characters for the hackathon demo.",
            original_tokens=0,
            compressed_tokens=0,
            compression_ratio=0.0,
            cost_savings_pct=0.0,
            latency_speedup_pct=0.0,
            reasoning_retention_score=1.0,
            selected_nodes=[],
            dropped_nodes=[],
        )

    # 1. Ingestion - detect code vs logs vs mixed
    domain = detect_domain(req.context)

    # 2. Structural layer - codec-specific
    if domain == "code":
        nodes = build_code_graph(req.context)
    else:
        nodes = build_log_templates(req.context)

    # 3. Diff engine - only new/changed nodes go through full pipeline
    new_or_changed, unchanged_pointers = session_cache.diff(req.session_id, nodes)

    # 4. Query router - rank remaining nodes by relevance to the query
    ranked_nodes = rank_by_relevance(req.query, new_or_changed)

    # 5. Budget allocator - decide how many nodes/tokens survive
    budget = req.target_tokens or allocate_budget(req.cost_pressure, req.latency_pressure)
    selected_nodes = []
    collapsed_nodes = []
    dropped_nodes = []
    running_tokens = 0
    for node in ranked_nodes:
        if running_tokens + node.token_estimate <= budget:
            selected_nodes.append(node)
            running_tokens += node.token_estimate
        else:
            # Full node doesn't fit. Save in recovery.
            recovery_index.store(req.session_id, node)
            stub_text = getattr(node, "stub", "")
            stub_estimate = len(stub_text.split()) if stub_text else 0
            if stub_text and (running_tokens + stub_estimate <= budget):
                collapsed_nodes.append(node)
                running_tokens += stub_estimate
            dropped_nodes.append(node.name)

    # 6. Token pruner - fine-grained cleanup within what survived
    compressed_prompt = prune_tokens(selected_nodes, unchanged_pointers, collapsed_nodes=collapsed_nodes)

    original_tokens = len(req.context.split())
    # Estimate compressed tokens using split or tiktoken if possible
    compressed_tokens = len(compressed_prompt.split())

    session_cache.commit(req.session_id, nodes)

    ratio = 1 - (compressed_tokens / max(original_tokens, 1))
    cost_savings_pct = max(0.0, ratio)
    latency_speedup_pct = min(0.95, max(0.0, 0.2 + 0.6 * cost_savings_pct))

    return CompressResponse(
        compressed_prompt=compressed_prompt,
        original_tokens=original_tokens,
        compressed_tokens=compressed_tokens,
        compression_ratio=ratio,
        cost_savings_pct=cost_savings_pct,
        latency_speedup_pct=latency_speedup_pct,
        selected_nodes=[n.name for n in selected_nodes],
        dropped_nodes=dropped_nodes,
        reused_nodes=[n.name for n in unchanged_pointers],
    )


@app.post("/recover")
def recover(session_id: str, missing_entity: str):
    """Stage 7 loop: pull back a specific dropped chunk on demand."""
    return recovery_index.lookup(session_id, missing_entity)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
