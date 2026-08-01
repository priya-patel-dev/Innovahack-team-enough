# TrustLayer — Autonomous Multi-Agent Research & Fact-Verification System

### 🏆 InnovaHack Chapter-1 · Domain 3 (Gen AI) · Problem Statement 1
**Team Name:** enough  

---

## 📌 Problem Statement

Standard AI research assistants and search-and-summarize wrappers often present unverified claims, hallucinated assertions, and false information with high confidence. Because these systems lack rigorous cross-referencing and validation mechanisms, automated research remains unreliable for critical tasks, leading to the propagation of misinformation.

## 🔍 Why It Matters

Fact-checking is a high-latency, expensive process. When organizations rely on automated AI tools, they risk accepting hallucinations as truth. Most existing AI wrappers perform a simple LLM query over search results without validating the consistency, source credibility, or timeline of the facts. A cost-effective, automated, and tiered verification engine is needed to separate truth from hallucination in real-time.

## 💡 Proposed Solution (High-Level)

**TrustLayer** is an autonomous multi-agent courtroom designed for zero-trust fact-verification. 
1. **Research Agent**: Crawls the web based on user input, retrieves 4-6 authoritative sources, and extracts specific factual claims.
2. **Tiered Verification Engine**:
   - **Stage 1 (Fast Signals)**: Lightweight, non-LLM check analyzing structural anomalies and timelines to compute a suspicion score.
   - **Stage 2 (Consolidated Audit)**: If flagged as suspicious or missing sources, performs Cross-Document Consistency, Multi-Query Stability, and Round-Trip Question Generation.
3. **Synthesis Agent**: Weighs agent consensus signals and tags claims with visual badges (**Verified** 🟢, **Ambiguous** 🟡, or **Flagged** 🔴).
4. **Human-in-the-Loop Panel**: Routes non-verified (yellow/red) claims to editors for manual final approval/rejection.

---

## 👥 Team Members

We are team **enough**:
* **Priya Patel** — Team Leader & Core Developer
* **Shweta Sharma** — Core Developer & Git Integrator
* **Archi Chovatiya** — Frontend Developer & UI Designer
* **Vaidehi Mangrolia** — QA Engineer & System Tester

---

## 🛠️ Tech Stack (Tentative)

* **Frontend**: React.js / HTML5 / Vanilla CSS (Responsive UI Dashboard)
* **Backend**: Node.js + Express (Vercel Serverless Functions)
* **LLM Engine**: Gemini API (Gemini 2.0 Flash / Gemini 1.5 Pro)
* **Search API**: Tavily Search API / Serper API
* **Similarity/Embeddings**: Client-side cosine similarity or lightweight embedding API
* **Deployment**: Vercel

---

## 📂 Repository Structure (Planned)

```
project/
├── backend/          # Server logic, APIs, and database handlers
├── frontend/         # Frontend dashboard console and review UI
├── ai/               # Multi-agent classes (Research, Verification, Synthesis)
├── docs/             # Documentation, slide decks, and design documents
├── tests/            # Unit testing and planted false-claim test cases
├── scripts/          # Automation and setup scripts
├── data/             # Local datasets and mock search payloads
├── assets/           # Media, design mockups, and presentations
├── notebooks/        # Prototyping, prompt testing, and research logs
├── .gitignore        # Version control file exclusions
├── requirements.txt  # Python requirements (if needed for utility scripts)
└── README.md         # This project overview and guide
```
