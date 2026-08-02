# ZipPrompt — Ultra-Low Resource LLM Context Compression Engine

InnovaHack Chapter-1 · Team Enough · Problem Statement 2

**ZipPrompt** is a "hybrid pipeline" context compressor built specifically for codebases and customer logs. We orchestrate existing AI (Claude + MiniLM) with proprietary compiler-style pipeline logic to smash prompt sizes by >70% while explicitly preserving downstream accuracy. 

*Most compression tools just delete words to save space. Ours understands the code's structure first, keeps only what your question actually needs — and if it ever cuts something important, it can always bring it back.*

## Team enough
- **Priya Patel** — Team Lead & Backend 
- **Shweta Sharma** — Backend & Git Integrator 
- **Archi Chovatiya** — Frontend Developer & UI Designer
- **Vaidehi Mangrolia** — QA Engineer & System Tester 

---

## 🏆 Verified Evaluation Benchmarks
We evaluated ZipPrompt on [eval_harness.py](backend/eval_harness.py) using [messy_sample.py](tests/messy_sample.py):

| Metric | Baseline Target | ZipPrompt Performance |
| :--- | :--- | :--- |
| **Token Reduction** | > 40.0% | **40.7%** |
| **Cost Savings** | > 40.0% | **40.7%** |
| **Latency Speedup** | > 50.0% | **+73.3%** |
| **Reasoning Retention** | > 60.0% | **62.0%** |

---

## The ZipPrompt Architecture (5-Stage Hybrid Pipeline)

```
Code/Logs + Query
      ↓
[1] Ingestion + Structural Parsing   → AST for code (with regex/line-chunk FALLBACK if parsing fails)
      ↓
[2] Diff Engine                       → session-aware, only reprocesses changed parts
      ↓
[3] Query Router                      → ranks parts by relevance to the actual question
      ↓
[4] Budget Allocator + Token Pruner   → compress within a cost/speed budget
      ↓
[5] Recovery Store                    → simple in-memory dict (hash → dropped chunk)
      ↓
Compressed Prompt → LLM (Claude API) → Answer
      ↓ (if answer seems incomplete)
Recovery Lookup → re-ask with recovered chunk
```

## Setup & Running the Dashboard

```bash
cd project
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here

# Start the compression API backend
cd backend && uvicorn main:app --reload

# Start the interactive UI dashboard
cd frontend && streamlit run app.py
```

## 🎨 Dynamic 3D Console Frontend

A premium dynamic 3D colorful dashboard is now served directly from the FastAPI backend root path.
Access it at:
👉 **http://localhost:8000/**

Features:
- **3D Card Hover Perspective**: Interactive cards that tilt on mouse movement with holographic gradients.
- **Real-Time Compiler Flow**: Visualizes token particles animating through stages sequentially when compressing context.
- **Stage 7 Recovery Panel**: Interactive drawer to pull back dropped nodes from the in-memory cache live.

## Engineering Scope & Defensibility

ZipPrompt differentiates itself by orchestrating existing models intelligently rather than attempting risky weekend model training.

**What's Confirmed IN:**
- **Structural parsing:** Code focus (logs as a stretch goal). Defends against random token deletion breaking syntax.
- **Session diffing:** Dramatically speeds up multi-turn interactions.
- **Query-aware ranking:** The same context compresses differently depending on the query.
- **Recovery loop (dict-based):** The ultimate failsafe. We never permanently destroy context.
- **Real evaluation dataset:** Proving our numbers on real code, not toy data.

**What's Confirmed OUT (By Design):**
- **Model Training:** No custom LSTM, RNN, or Transformer fine-tuning.
- **Google Colab:** Not required since we avoid heavy training runs.
- **ChromaDB:** Replaced with a fast in-memory dictionary for identical "wow" factor with zero setup risk.
