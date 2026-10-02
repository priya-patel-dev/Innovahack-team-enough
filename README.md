# ZipPrompt

Ultra-low-resource LLM context compression engine for codebases and operational knowledge workflows.

## Overview
ZipPrompt is a hybrid context-compression system built to reduce prompt size while preserving the most relevant information for reasoning. It is designed for code-heavy, knowledge-heavy, and high-context AI workflows where token efficiency matters.

## Problem It Solves
Most compression tools simply remove words or tokens without understanding structure. ZipPrompt takes a smarter approach by parsing context based on meaning, structure, and relevance, then compresses only what is necessary to preserve the useful signal.

## Key Features
- Context compression for large code and log inputs
- Query-aware relevance filtering
- Recovery mechanism for important dropped context
- Better cost, latency, and reasoning efficiency
- Interactive dashboard for tradeoff tuning

## Team
- Priya Patel — Team Lead & Backend
- Shweta Sharma — Backend & Git Integrator
- Archi Chovatiya — Frontend Developer & UI Designer
- Vaidehi Mangrolia — QA Engineer & System Tester

## Evaluation Highlights
ZipPrompt was evaluated on a real enterprise-style codebase and showed strong improvement in token reduction, cost savings, latency, and reasoning retention.

## Architecture
```text
Code / Logs + Query
      ↓
[1] Ingestion + Structural Parsing
      ↓
[2] Diff Engine
      ↓
[3] Query Router
      ↓
[4] Budget Allocator + Token Pruner
      ↓
[5] Recovery Store
      ↓
Compressed Prompt → LLM → Answer
```

## Setup & Run
```bash
cd project
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here

# Start the backend
cd backend && uvicorn main:app --reload

# Start the dashboard
cd frontend && streamlit run app.py
```

## Dashboard
The project includes a dynamic 3D-style interactive dashboard served from the backend and designed to visualize compression stages, tradeoffs, and recovery behavior.

## Project Goal
To make large-context AI interactions more efficient, affordable, and practical without sacrificing reasoning quality.

## My Contribution
This project centered on designing and implementing a hybrid compression pipeline with a strong focus on usability, real-world evaluation, and practical LLM efficiency.

## Status
Hackathon-grade solution / portfolio project
