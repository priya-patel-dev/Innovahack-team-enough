"""
ZipPrompt backend entrypoint.

Pipeline order (see PLANNING.md for the full diagram):
  ingestion -> structural codec -> diff engine -> query router
  -> budget allocator -> token pruner -> recovery index -> LLM call
"""
from fastapi import FastAPI
from pydantic import BaseModel

from ingestion import detect_domain
from codecs.code_codec import build_code_graph
from codecs.log_codec import build_log_templates
from diff_engine import SessionCache
from query_router import rank_by_relevance
from budget_allocator import allocate_budget
from token_pruner import prune_tokens
from recovery_index import RecoveryIndex

app = FastAPI(title="ZipPrompt")

session_cache = SessionCache()
recovery_index = RecoveryIndex()


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


@app.post("/compress", response_model=CompressResponse)
def compress(req: CompressRequest) -> CompressResponse:
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
    running_tokens = 0
    for node in ranked_nodes:
        if running_tokens + node.token_estimate > budget:
            recovery_index.store(req.session_id, node)  # keep it recoverable
            continue
        selected_nodes.append(node)
        running_tokens += node.token_estimate

    # 6. Token pruner - fine-grained cleanup within what survived
    compressed_prompt = prune_tokens(selected_nodes, unchanged_pointers)

    original_tokens = sum(n.token_estimate for n in nodes)
    compressed_tokens = len(compressed_prompt.split())  # replace with tiktoken count

    session_cache.commit(req.session_id, nodes)

    return CompressResponse(
        compressed_prompt=compressed_prompt,
        original_tokens=original_tokens,
        compressed_tokens=compressed_tokens,
        compression_ratio=1 - (compressed_tokens / max(original_tokens, 1)),
    )


@app.post("/recover")
def recover(session_id: str, missing_entity: str):
    """Stage 7 loop: pull back a specific dropped chunk on demand."""
    return recovery_index.lookup(session_id, missing_entity)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
