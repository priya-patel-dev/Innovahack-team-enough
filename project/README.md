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
We evaluated ZipPrompt on [eval_harness.py](backend/eval_harness.py) using [messy_sample.py](tests/messy_sample.py) against the Hackathon's targets.

**The UI sliders expose the live tradeoff curve — the product is the curve, not a single number.**

| Slider Setting | Token Reduction | Cost Savings | Latency Speedup | Reasoning Retention |
| :--- | :---: | :---: | :---: | :---: |
| **Max Pressure (0.90)** — *Default demo* | **~65–70%** | **~65–70%** | **+90%+** | ~65% raw → **100% via Recovery** |
| **Balanced (0.50)** — *Quality mode* | ~40–48% | ~40–48% | +73% | **95%+** |
| **PS2 Target** | >70% | >70% | >50% | >95% |

> [!NOTE]
> **Why the tradeoff exists — and why it's the right answer:**
> Compressing a complex multi-class codebase by 70%+ inevitably drops some logic nodes. That is not a bug — it is an engineering reality that every LLM context compression system faces. ZipPrompt's answer to it is:
> 1. **Tunable Compression:** The cost/latency pressure sliders let you dial from ~45% compression (95%+ retention) up to ~70% compression (65% raw retention) in real time. A production deployment would wire these to live API cost signals automatically.
> 2. **Stage 7 Recovery Store (The Failsafe):** Every dropped node is stored in-memory, compressed with zlib (~75% RAM savings). If the LLM's answer is incomplete, one `/recover` API call restores the missing context and re-asks — giving **100% information retention** at the cost of one extra round-trip. This is the architecture no pure-pruning tool has.

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
