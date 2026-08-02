# Hackathon Planning & Evaluation - ZipPrompt

**Hackathon:** InnovaHack Chapter-1
**Date:** August 1, 2026 – August 2, 2026
**Team Name:** Team Enough

---

## Hour 2: Problem Statement Selection & Brainstorming

### Selected Problem Statement

**Problem Statement 2: Ultra-Low Resource LLM Context Compression Engine**

- **Project Name:** `ZipPrompt`
- **Core Goal:** Build an algorithmic token pre-processor that strips semantic redundancy from prompts, compressing context by 70%+ while retaining 95%+ downstream accuracy.

---

## Project Concept & Architecture: "ZipPrompt"

Instead of a single-pass token pruner (the common approach most teams will build),
ZipPrompt is a **compiler-style pipeline**: raw context is converted into a structured
representation, diffed against session history, ranked against the live query, and
only then pruned at the token level. Anything dropped stays recoverable.

```
Raw Context (code/logs) + Query
        |
        v
[1] Ingestion Layer        -> domain detection (code vs logs), picks codec
        |
        v
[2] Structural Layer       -> AST/dependency graph (code)
        |
        v
[3] Diff Engine            -> session cache; only new/changed nodes go
    (session-aware)            through full pipeline, unchanged = pointer
        |
        v
[4] Query Router           -> TF-IDF embedding-less similarity with signature/name boosting
        |
        v
[5] Budget Allocator       -> adaptive compression ratio based on a
                               cost/latency signal (demo: UI slider)
        |
        v
[6] Token Pruner           -> syntax-preserving rule-based cleanup (comments stripping, docstring truncation)
        |
        v
[7] Recovery Index         -> dropped content indexed in-memory;
                               pulled back on demand if answer needs it
        |
        v
Compressed Prompt --> Target LLM (Claude API) --> Answer
                               |
                               v (if answer signals missing info)
                        Recovery Lookup --> re-ask with recovered chunk
```

### Why this is different
Most teams will build a single LLMLingua-style perplexity pruner. ZipPrompt's
differentiators, in order of how novel/defensible they are:

1. **Structural conversion before pruning** — code becomes a call/dependency graph,
   so redundancy is removed by representation change, not just deletion.
2. **Query-aware compression** — the same context compresses differently depending
   on what's being asked, directly improving the "reasoning retention" metric.
3. **Session-aware diffing** — repeat turns in a session only pay for what changed,
   directly targeting the "real-time interactions" pain point in the problem
   statement.
4. **Adaptive budget** — compression ratio reacts to a cost/latency signal instead
   of being a fixed percentage.
5. **Recoverable compression** — dropped content isn't gone, it's indexed and can
   be retrieved if the target LLM's answer needs it.

### Backend (Python/FastAPI)
- `ingestion.py` — domain detection, codec routing
- `custom_codecs/code_codec.py` — AST-based call/dependency graph builder
- `diff_engine.py` — session cache, node hashing, diffing
- `query_router.py` — TF-IDF based relevance scoring with stemming and name boosting
- `budget_allocator.py` — adaptive token budget allocation based on sliders
- `token_pruner.py` — rule-based pruner (comments, blank lines, docstring truncation)
- `recovery_index.py` — in-memory store for dropped content + keyword lookup
- `eval_harness.py` — compression ratio / cost reduction / reasoning retention / latency speedup evaluation (runs live Claude API or Mock mode fallbacks)

### Frontend (Dashboard)
- Split view: original vs compressed prompt with code highlighting
- Live metrics panel: compression ratio, token count, cost savings, latency speedup
- Budget sliders to demo adaptive compression live
- AST node allocation block: shows selected (green) vs dropped (red) nodes in the pipeline
- "Recovery" panel showing a dropped chunk being retrieved live from the in-memory cache

---

## Hour 2 Commit Verification
- **Action:** Update project plan with the 5-pillar architecture and file scaffold.
- **Selected Stack:** Python (FastAPI, tiktoken, ast) for backend + Streamlit for dashboard.
- **Target LLM for eval:** Claude API (Sonnet)

## Hour 3 Commit Verification
- **Action:** Scaffold `project/backend` and `project/frontend` folders with module stubs and `requirements.txt`.

## Hour 4 Commit Verification
- **Action:** Refactored pipeline to pure-Python implementations to remove heavy deep learning dependencies.
- **Details:** 
  - Renamed `codecs` folder to `custom_codecs` to resolve standard library namespace collisions.
  - Implemented pure-Python TF-IDF similarity with a custom suffix-stripping stemmer and name-boosting (5.0x weight) in `query_router.py`.
  - Implemented syntax-preserving rule-based pruner (comment stripper, whitespace compressor, docstring truncator) in `token_pruner.py`.
  - Integrated duplicate-prevention cache and chromadb-like return schema in `recovery_index.py`.
  - Created and ran `project/tests/test_pipeline_e2e.py` verifying the full pipeline end-to-end (Stage 1 to 7) in under 5ms.

## Hour 5 Commit Verification
- **Action:** Implemented evaluation harness and wired metrics to Streamlit UI.
- **Details:**
  - Implemented `project/backend/eval_harness.py` featuring live Claude API support and automated Mock mode fallback (if API key is missing) with pure-Python cosine similarity.
  - Generated performance report in `project/results.md` showing a 44.9% token reduction, 73.3% latency speedup, and 62% accuracy retention on `messy_sample.py`.
  - Upgraded Streamlit `project/frontend/app.py` with dynamic metrics card board, AST Node allocation visualizer, default example loader, and interactive Stage 7 recovery store lookup.

## Hour 6 Commit Verification (H1 & H2)
- **Action:** Tuned default budget ceilings, TF boosting, and corrected AST node duplication.
- **Details:**
  - Tuned `project/backend/budget_allocator.py` values to scale pressure damping to 0.85 and raised limits.
  - Corrected nested method duplication inside class unparse walks in `project/backend/custom_codecs/code_codec.py` to prevent redundant tokens.
  - Regenerated `project/results.md` locking down **40.7% token reduction** at **62.0% reasoning retention** on `messy_sample.py`.

## Hour 7 Commit Verification (H3)
- **Action:** Added unit tests and synchronized metrics card values.
- **Details:**
  - Wrote `project/tests/test_query_router.py` testing ranking and stemming weights on function name matches.
  - Integrated the verified 40.7% compression metrics as the default values in `project/frontend/console.html`.

## Hour 8 Commit Verification (H4 & H5)
- **Action:** Enabled CORSMiddleware, hardened recovery loop lookup, and built origin-robust fetch routing.
- **Details:**
  - Configured `CORSMiddleware` in `project/backend/main.py` allowing wildcard headers and origins.
  - Added dynamic protocol checking to console fetches to prevent local drive file CORS failures.
  - Implemented query expansion alias mapping (constructor -> `__init__`, getters -> `get_`) inside `project/backend/recovery_index.py`.

## Hour 9 Commit Verification (H6 & H7 & H8)
- **Action:** Sanity checked repository, updated final logs, and rehearsed the demo playbook.
- **Details:**
  - Consolidated and verified planning scopes, finalizing full submission details.
  - Launched uvicorn backend hosting the premium 3D console live at `http://127.0.0.1:8000`.
