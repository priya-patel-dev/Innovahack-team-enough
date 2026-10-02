# ZipPrompt Evaluation Results
Generated on: 2026-08-03 09:09:15
Evaluation Mode: **LIVE API (Gemini (gemini-2.5-flash))**

## Core Metrics Summary
| Metric | Original | Compressed | Net Change / Score |
| :--- | :---: | :---: | :---: |
| **Token Count** | 4783 | 1423 | **70.2% reduction** |
| **Prompt Cost (USD)** | $0.014349 | $0.004269 | **70.2% savings** |
| **Average Latency** | 40.96s | 46.15s | **-12.7% speedup** |
| **Reasoning Retention** | 100.0% | 4.1% | **4.1% retention** |

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
By preserving the signature and high-relevance blocks in full while stripping boilerplate, the LLM retains functional context.
- **Reasoning Retention Score:** **4.1%** (semantic similarity of answers)

### 4. Live Model Response Verification (Raw Gemini Responses)

#### Question 1: "What is the name of the factory class defined in the code?"
- **Similarity Score**: 20.64%
- **Original Context Answer**:
  > The `AuthenticationService` class can be considered a factory class because it is responsible for creating new `UserProfile` instances through its `register_user` method.

It also instantiates other service classes (`SessionTokenManager` and `UserMetricsEngine`) internally, acting as an orchestrator and initializer of these components.
- **Compressed Context Answer**:
  > The `AuthenticationService` class, specifically its `register_user` method (even though collapsed), suggests it acts as a factory for `UserProfile` objects.

#### Question 2: "What are the instance variables initialized in the constructor of the factory?"
- **Similarity Score**: 0.00%
- **Original Context Answer**:
  > 
- **Compressed Context Answer**:
  > 

#### Question 3: "What does calculate_complex_user_metrics return if the user is not active?"
- **Similarity Score**: 0.00%
- **Original Context Answer**:
  > 
- **Compressed Context Answer**:
  > 

#### Question 4: "What multiplier is applied to the base score if the score exceeds 100 in calculate_complex_user_metrics?"
- **Similarity Score**: 0.00%
- **Original Context Answer**:
  > 
- **Compressed Context Answer**:
  > 

#### Question 5: "What is the return structure of calculate_complex_user_metrics on a successful run?"
- **Similarity Score**: 0.00%
- **Original Context Answer**:
  > 
- **Compressed Context Answer**:
  > 

