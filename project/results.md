# ZipPrompt Evaluation Results
Generated on: 2026-08-02 13:30:07
Evaluation Mode: **LIVE API (Gemini)**

## Core Metrics Summary
| Metric | Original | Compressed | Net Change / Score |
| :--- | :---: | :---: | :---: |
| **Token Count** | 4783 | 1423 | **70.2% reduction** |
| **Prompt Cost (USD)** | $0.014349 | $0.004269 | **70.2% savings** |
| **Average Latency** | 1.40s | 0.52s | **62.8% speedup** |
| **Reasoning Retention** | 100.0% | 100.0% | **100.0% retention** |

## Detail Analysis

### 1. Context Compression Efficiency
ZipPrompt parsed the codebase context into structural AST components, filtered it using a query-aware TF-IDF router, tracked the session diff cache, and cleaned up whitespace/comments.
- **Original Context Size:** 4783 tokens
- **Compressed Context Size:** 1423 tokens
- **Total Saved Space:** 3360 tokens (70.2%)

### 2. Cost Analysis (Standard Anthropic Claude Pricing)
- **Original Cost per 10k requests:** $143.49
- **Compressed Cost per 10k requests:** $42.69
- **Net Savings per 10k requests:** $100.80

### 3. Reasoning and Downstream Quality Retention
By preserving the signature and high-relevance blocks in full while stripping boilerplate, the LLM retains almost all functional context.
- **Reasoning Retention Score:** **100.0%** (semantic similarity of answers)
