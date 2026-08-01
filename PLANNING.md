# Hackathon Planning & Evaluation

**Hackathon:** InnovaHack Chapter-1
**Date:** August 1, 2026 – August 2, 2026
**Team Name:** Team Enough

---

## Hour 1: Problem Statement Evaluation

We are evaluating two potential problem statements for the hackathon. Below is the brainstorming and analysis of both paths.

### Option 1: Multi-Modal Knowledge Graph Synthesis for Enterprise Compliance

#### Concept:
An intelligent compliance assistant that reads heterogeneous documents (PDF regulations, audio logs, data tables, system schematics), extracts an entity-relationship web (knowledge graph), and uses Graph RAG to answer queries with high accuracy and zero hallucinations.

#### Pros & Cons:
*   **Pros:**
    *   **High Demo Value:** We can build a visually stunning frontend showing an interactive node-link graph visualization of the compliance connections. Judges love visual demos.
    *   **Clear Value Proposition:** Direct enterprise applicability (risk reduction, compliance auditing).
    *   **Generative AI Synergy:** Leverages multi-modal LLMs (like Gemini) to easily parse audio, tables, and images of schematics directly into structured JSON graphs.
*   **Cons:**
    *   Ingesting multiple complex formats (audio, schematics) requires a solid pipeline. We must keep the graph database lightweight (e.g., using NetworkX or Neo4j-in-memory).

---

### Option 2: Ultra-Low Resource LLM Context Compression Engine

#### Concept:
An algorithmic token pre-processor (similar to LLMLingua) that strips semantic redundancy and boilerplate from long-context prompts, reducing prompt size by 70%+ while retaining 95%+ reasoning accuracy.

#### Pros & Cons:
*   **Pros:**
    *   **Deep Technical Depth:** Strong algorithm-focused project that appeals to technical judges.
    *   **Clear Metrics:** Very easy to benchmark and graph (Compression Ratio, Latency Speedup, Cost Reduction).
*   **Cons:**
    *   **Low Visual Appeal:** Hard to make a visually engaging demo. It's mostly backend middleware or a command-line utility.
    *   **Algorithmic Complexity:** Fine-tuning or implementing semantic compression algorithms under a 30-hour limit can be high-risk and hard to debug.

---

## Choice & Next Steps

*   **Selected Problem Statement:** [TBD - Currently deciding between Option 1 and Option 2]
*   **Core Objective:** Build a functional end-to-end prototype matching the chosen statement.
