# ZipPrompt — Ultra-Low Resource LLM Context Compression Engine

InnovaHack Chapter-1 · Team Enough · Problem Statement 2

See `PLANNING.md` for the full architecture and rationale. This README is
the hour-by-hour execution + commit plan for the remaining hours.

Each row = one commit, tagged with an `## Hour N Commit Verification` entry
appended to `PLANNING.md` (matches the pattern already started there).

## Team

We are team **enough**:
- **Priya Patel** — Team Lead & Backend (pipeline architecture, structural layer)
- **Shweta Sharma** — Backend & Git Integrator (diff engine, eval harness, repo/commits)
- **Archi Chovatiya** — Frontend Developer & UI Designer (dashboard, live metrics view)
- **Vaidehi Mangrolia** — QA Engineer & System Tester (eval harness verification, demo hardening)

*(Roles carried over from planning — adjust above if anyone's actual focus shifted after the pivot to Problem Statement 2.)*

## Hour-by-hour plan

| Hours | What to build | What to commit | PLANNING.md entry |
|---|---|---|---|
| **H3–H4** | Wire `ingestion.py` + both codecs (`code_codec.py`, `log_codec.py`) into a working pair — feed sample code + sample logs, confirm nodes come out with sane token estimates | `backend/ingestion.py`, `backend/codecs/*` with real test output pasted into commit message or a `tests/sample_output.md` | "Structural layer working for code + logs, verified on sample data" |
| **H5–H6** | `diff_engine.py` — simulate two turns in the same session, prove unchanged nodes get pointer-collapsed | `backend/diff_engine.py` + a small script/notebook showing turn 1 vs turn 2 token savings | "Session-aware diffing verified: turn 2 reuses N unchanged nodes" |
| **H7–H8** | `query_router.py` — embed a sample query + nodes, confirm ranking makes sense (most relevant function/log template floats to top) | `backend/query_router.py` + example ranking output | "Query-aware ranking verified on sample query" |
| **H9** | `budget_allocator.py` — trivial but needed before pruner; wire the cost/latency sliders to it | `backend/budget_allocator.py` | "Adaptive budget allocator wired" |
| **H10–H11** | `token_pruner.py` — get llmlingua actually compressing selected nodes end-to-end; handle the "fail open" case if llmlingua errors on weird input | `backend/token_pruner.py` tested against real node output from H3-H4 | "Token pruning integrated, fallback tested" |
| **H12** | `recovery_index.py` — store dropped nodes, do one manual lookup, confirm chromadb round-trips correctly | `backend/recovery_index.py` | "Recovery index storing + retrieving dropped chunks" |
| **H13** | Wire all 7 stages together in `main.py`, hit `/compress` with curl/Postman, fix integration bugs (this step always takes longer than expected — budget extra time here if something else runs short) | working `main.py` + a `curl` example in README | "End-to-end pipeline working via /compress endpoint" |
| **H14–H15** | `eval_harness.py` — run real compression ratio / cost / retention / latency numbers against Claude API on your actual sample code+logs | `backend/eval_harness.py` + a `results.md` with real numbers from a real run (this is your proof for judges) | "First real eval numbers: X% compression, Y% retention" |
| **H16–H17** | Frontend: `frontend/app.py` (Streamlit) wired to the live backend — split view, metrics, budget slider actually working | `frontend/app.py` fully wired, screenshot in commit | "Dashboard wired to live backend, demo-able end to end" |
| **H18** | Recovery panel in the dashboard — show a dropped chunk getting pulled back live when asked a question the compressed prompt can't answer. This is your most novel demo moment, don't cut it if you're tight on time | dashboard update + short demo clip/gif if possible | "Recovery loop demoed live in dashboard" |
| **H19** | Polish: error handling for demo-day flakiness (API timeouts, empty input, huge paste), fallback sample data pre-loaded so a live-typing failure doesn't kill the demo | small fixes across files | "Demo hardening: fallbacks + error handling" |
| **H20** | Final `README.md` update with architecture diagram, real results table, and setup/run instructions. Rehearse the pitch: lead with the 3 differentiators (structural conversion, query-aware, session diffing) before mentioning token pruning at all | final `README.md` | "Final submission: docs + results + demo instructions" |

## Priority order if you run out of time

If something has to get cut, cut in this order (least to most damaging to
your pitch):

1. Recovery index (Stage 7) — nice narrative, not load-bearing for the core metrics
2. Adaptive budget allocator sophistication — a hardcoded slider-to-number mapping is fine
3. Log codec — if code is stronger/faster to demo, lean on code and mention logs as "same architecture, second codec" in the pitch
4. Never cut: structural layer (#1 differentiator), query router (#2), diff engine (#5) — these three are what separates you from every other LLMLingua-clone team

## Setup

```bash
cd project
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here

# terminal 1
cd backend && uvicorn main:app --reload

# terminal 2
cd frontend && streamlit run app.py
```

## Architecture

See `PLANNING.md` for the full pipeline diagram and rationale.
