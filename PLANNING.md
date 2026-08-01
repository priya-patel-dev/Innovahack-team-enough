# Hackathon Planning & Evaluation

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
[2] Structural Layer       -> AST/dependency graph (code) or event-template
    (codec: code/logs)        mining via Drain (logs)
        |
        v
[3] Diff Engine            -> session cache; only new/changed nodes go
    (session-aware)            through full pipeline, unchanged = pointer
        |
        v
[4] Query Router           -> embeds query + nodes, ranks by relevance
        |
        v
[5] Budget Allocator       -> adaptive compression ratio based on a
                               cost/latency signal (demo: UI slider)
        |
        v
[6] Token Pruner           -> llmlingua-style fine cleanup within budget
        |
        v
[7] Recovery Index         -> dropped content embedded/stored (chromadb);
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
   logs become event templates, so redundancy is removed by representation change,
   not just deletion.
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
- `codecs/code_codec.py` — AST-based call/dependency graph builder
- `codecs/log_codec.py` — Drain-based log template mining
- `diff_engine.py` — session cache, node hashing, diffing
- `query_router.py` — embedding-based relevance scoring (MiniLM)
- `budget_allocator.py` — adaptive token budget allocation
- `token_pruner.py` — llmlingua wrapper, fine-grained cleanup
- `recovery_index.py` — chromadb store for dropped content + lookup
- `eval_harness.py` — compression ratio / cost reduction / reasoning
  retention / latency speedup, measured against the Claude API

### Frontend (Dashboard)
- Split view: original vs compressed prompt with diff highlighting
- Live metrics panel: compression ratio, token count, cost savings, latency
- Budget slider to demo adaptive compression live
- "Recovery" panel showing a dropped chunk being retrieved live

---

## Hour 2 Commit Verification
- **Action:** Update project plan with the 5-pillar architecture and file scaffold.
- **Selected Stack:** Python (FastAPI, llmlingua, drain3, sentence-transformers,
  chromadb, tiktoken) for backend + Streamlit (fallback: React) for dashboard.
- **Target LLM for eval:** Claude API (Sonnet)

## Hour 3 Commit Verification
- **Action:** Scaffold `project/backend` and `project/frontend` folders with
  module stubs and `requirements.txt`. No logic yet beyond interfaces —
  establishes contracts between pipeline stages before implementation.

<!-- Continue this pattern: one "## Hour N Commit Verification" entry per
     checkpoint commit, see hourly plan in README.md for what goes in each. -->
