"""
ZipPrompt Production Backend API.

Pipeline:
  1. Ingestion Layer      -> Domain detection (code vs logs vs text)
  2. Structural Layer     -> AST call-graph parser (code) or Drain3 template miner (logs)
  3. Diff Engine          -> Multi-tenant session caching & delta extraction
  4. Query Router         -> Hybrid BM25/TF-IDF scoring with call-graph expansion
  5. Budget Allocator     -> Dynamic token ceiling calculation
  6. Token Pruner         -> AST skeleton reconstruction and syntax preservation
  7. Recovery Index       -> Tenant-isolated, thread-safe on-demand recovery
"""
import os
import time
from typing import Optional, Any
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ingestion import detect_domain
from custom_codecs.code_codec import build_code_graph, estimate_tokens
from custom_codecs.log_codec import build_log_templates
from diff_engine import SessionCache
from query_router import rank_by_relevance, CONFIDENCE_THRESHOLD
from budget_allocator import allocate_budget
from token_pruner import prune_tokens
from recovery_index import RecoveryIndex

app = FastAPI(
    title="ZipPrompt Context Compression API",
    description="Compiler-style LLM context compression engine with AST structural preservation and recovery indexing.",
    version="2.0.0"
)

# Configurable CORS
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if "*" not in allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_cache = SessionCache()
recovery_index = RecoveryIndex()


@app.get("/", response_class=HTMLResponse)
def read_root():
    """Serves the 3D console frontend."""
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    html_path = os.path.join(frontend_dir, "console.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h2>ZipPrompt API Running. (console.html not found in frontend directory)</h2>")


class CompressRequest(BaseModel):
    session_id: str = Field(default="default_session", description="Unique session ID for multi-turn diff caching.")
    tenant_id: str = Field(default="default", description="Tenant ID for enterprise data isolation.")
    query: str = Field(..., min_length=1, description="Question or task the model is addressing.")
    context: str = Field(..., min_length=1, description="Raw source code or log context.")
    target_tokens: Optional[int] = Field(default=None, ge=10, description="Explicit target token budget ceiling.")
    cost_pressure: float = Field(default=0.5, ge=0.0, le=1.0, description="Cost compression aggression.")
    latency_pressure: float = Field(default=0.5, ge=0.0, le=1.0, description="Latency compression aggression.")


class CompressResponse(BaseModel):
    compressed_prompt: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    cost_savings_pct: float
    latency_speedup_pct: float
    processing_time_ms: float
    confidence: float
    low_confidence: bool
    domain: str
    selected_nodes: list[str]
    collapsed_nodes: list[str]
    dropped_nodes: list[str]
    reused_nodes: list[str]


class RecoverRequest(BaseModel):
    session_id: str
    query_or_node_id: str
    tenant_id: str = "default"
    n_results: int = 1


@app.post("/compress", response_model=CompressResponse)
def compress(req: CompressRequest) -> CompressResponse:
    start_time = time.perf_counter()

    # 0. Validation
    if not req.context or not req.context.strip():
        raise HTTPException(status_code=400, detail="Context cannot be empty.")
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    if len(req.context) > 500_000:
        raise HTTPException(status_code=413, detail="Context exceeds maximum limit of 500K characters.")

    original_tokens = estimate_tokens(req.context)

    # 1. Ingestion: domain detection
    domain = detect_domain(req.context)

    # 2. Structural Layer
    if domain == "code":
        nodes = build_code_graph(req.context)
    else:
        nodes = build_log_templates(req.context)

    # 3. Diff Engine: session-aware delta detection
    new_or_changed, unchanged_pointers = session_cache.diff(req.session_id, nodes, tenant_id=req.tenant_id)

    # 4. Query Router: hybrid ranking with call-graph boost
    ranked_nodes, confidence = rank_by_relevance(req.query, new_or_changed)
    low_confidence = confidence < CONFIDENCE_THRESHOLD

    # 5. Budget Allocator
    budget = req.target_tokens or allocate_budget(
        req.cost_pressure,
        req.latency_pressure,
        context_tokens=original_tokens
    )

    selected_nodes = []
    collapsed_nodes = []
    dropped_nodes = []
    running_tokens = 0

    # Ensure critical header imports/constants are prioritized in code domain
    for node in nodes:
        if getattr(node, "kind", "") in ("import", "constant") and getattr(node, "parent_class", None) is None:
            if node not in selected_nodes:
                selected_nodes.append(node)
                running_tokens += getattr(node, "token_estimate", 0)

    # Allocate remaining budget across query-ranked nodes
    for node in ranked_nodes:
        if node in selected_nodes:
            continue

        cost = getattr(node, "token_estimate", 0)
        if running_tokens + cost <= budget:
            selected_nodes.append(node)
            running_tokens += cost
        else:
            # Store in recovery index
            recovery_index.store(req.session_id, node, tenant_id=req.tenant_id)
            stub_cost = estimate_tokens(getattr(node, "stub", ""))
            if stub_cost and (running_tokens + stub_cost <= budget + 200):
                collapsed_nodes.append(node)
                running_tokens += stub_cost
            dropped_nodes.append(getattr(node, "name", str(node)))

    # Ensure all non-selected nodes are archived in Stage 7 recovery store
    for node in nodes:
        if node not in selected_nodes:
            recovery_index.store(req.session_id, node, tenant_id=req.tenant_id)

    # 6. Token Pruner: Syntactic code assembly
    compressed_prompt = prune_tokens(
        selected_nodes=selected_nodes,
        unchanged_pointers=unchanged_pointers,
        collapsed_nodes=collapsed_nodes,
        all_nodes=nodes,
        domain=domain
    )

    compressed_tokens = estimate_tokens(compressed_prompt)

    # Update session snapshot
    session_cache.commit(req.session_id, nodes, tenant_id=req.tenant_id)

    processing_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
    ratio = max(0.0, 1.0 - (compressed_tokens / max(original_tokens, 1)))
    cost_savings_pct = ratio
    # Estimated time-to-first-token latency speedup based on token reduction
    latency_speedup_pct = max(0.0, min(0.90, ratio * 0.85))

    return CompressResponse(
        compressed_prompt=compressed_prompt,
        original_tokens=original_tokens,
        compressed_tokens=compressed_tokens,
        compression_ratio=round(ratio, 4),
        cost_savings_pct=round(cost_savings_pct, 4),
        latency_speedup_pct=round(latency_speedup_pct, 4),
        processing_time_ms=processing_time_ms,
        confidence=confidence,
        low_confidence=low_confidence,
        domain=domain,
        selected_nodes=[getattr(n, "name", str(n)) for n in selected_nodes],
        collapsed_nodes=[getattr(n, "name", str(n)) for n in collapsed_nodes],
        dropped_nodes=dropped_nodes,
        reused_nodes=[p.name for p in unchanged_pointers]
    )


@app.post("/recover")
def recover(
    session_id: Optional[str] = Query(None),
    missing_entity: Optional[str] = Query(None),
    query_or_node_id: Optional[str] = Query(None),
    tenant_id: str = Query("default"),
    n_results: int = Query(1),
    body: Optional[RecoverRequest] = None
):
    """Stage 7 Agentic Recovery: pulls back a pruned node by ID or keyword."""
    sid = (body.session_id if body else None) or session_id or "default_session"
    q = (body.query_or_node_id if body else None) or query_or_node_id or missing_entity or ""
    tid = (body.tenant_id if body else None) or tenant_id or "default"
    n = (body.n_results if body else None) or n_results or 1
    return recovery_index.lookup(
        session_id=sid,
        query=q,
        tenant_id=tid,
        n_results=n
    )


@app.get("/tool-schema")
def get_agent_tool_schema():
    """Returns JSON tool calling definition for Claude / GPT / Gemini agents."""
    return recovery_index.get_tool_spec()


@app.get("/health")
def health_check():
    """Liveness probe."""
    return {
        "status": "healthy",
        "service": "ZipPrompt",
        "version": "2.0.0"
    }


@app.get("/sample")
def get_sample_code():
    """Serves messy_sample.py for test runners and the frontend."""
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    path = os.path.join(data_dir, "messy_sample.py")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return PlainTextResponse(f.read())
    return PlainTextResponse("# Sample file not found.")


@app.get("/sample-log")
def get_sample_log():
    """Serves messy_sample.log for test runners and the frontend."""
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    path = os.path.join(data_dir, "messy_sample.log")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return PlainTextResponse(f.read())
    return PlainTextResponse("# Sample log not found.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
