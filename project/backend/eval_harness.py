"""
Evaluation harness - this is what proves your compression ratio/cost/
retention/latency claims live to judges. Arguably as important to build
well as the compressor itself.

Measures, comparing ORIGINAL prompt vs COMPRESSED prompt on the same
target LLM call:
  1. Compression ratio  - token count before/after
  2. Cost reduction     - tokens x $/token
  3. Reasoning retention- answer similarity on a fixed eval question set
  4. Inference latency speedup - wall-clock time before/after
"""
import os
import time
from dataclasses import dataclass, asdict

import tiktoken
from anthropic import Anthropic
from sentence_transformers import SentenceTransformer
import numpy as np

MODEL = "claude-sonnet-4-6"
# Approximate; check current Anthropic pricing page for exact $/token.
PRICE_PER_1K_INPUT_TOKENS = 0.003

_encoder = tiktoken.get_encoding("cl100k_base")
_embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


@dataclass
class EvalResult:
    compression_ratio: float
    original_tokens: int
    compressed_tokens: int
    cost_reduction_pct: float
    original_cost_usd: float
    compressed_cost_usd: float
    reasoning_retention_score: float  # cosine similarity of answers, 0-1
    original_latency_s: float
    compressed_latency_s: float
    latency_speedup_pct: float


def _count_tokens(text: str) -> int:
    return len(_encoder.encode(text))


def _ask_llm(prompt: str, question: str) -> tuple[str, float]:
    start = time.time()
    resp = _client.messages.create(
        model=MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": f"{prompt}\n\nQuestion: {question}"}],
    )
    elapsed = time.time() - start
    answer = "".join(block.text for block in resp.content if hasattr(block, "text"))
    return answer, elapsed


def _answer_similarity(a: str, b: str) -> float:
    vecs = _embed_model.encode([a, b])
    sim = vecs[0] @ vecs[1] / (
        np.linalg.norm(vecs[0]) * np.linalg.norm(vecs[1]) + 1e-8
    )
    return float(sim)


def run_eval(original_prompt: str, compressed_prompt: str, eval_questions: list[str]) -> EvalResult:
    orig_tokens = _count_tokens(original_prompt)
    comp_tokens = _count_tokens(compressed_prompt)

    orig_answers, comp_answers = [], []
    orig_latencies, comp_latencies = [], []

    for q in eval_questions:
        oa, ol = _ask_llm(original_prompt, q)
        ca, cl = _ask_llm(compressed_prompt, q)
        orig_answers.append(oa)
        comp_answers.append(ca)
        orig_latencies.append(ol)
        comp_latencies.append(cl)

    retention_scores = [
        _answer_similarity(o, c) for o, c in zip(orig_answers, comp_answers)
    ]

    orig_cost = orig_tokens / 1000 * PRICE_PER_1K_INPUT_TOKENS
    comp_cost = comp_tokens / 1000 * PRICE_PER_1K_INPUT_TOKENS
    orig_lat = sum(orig_latencies) / len(orig_latencies)
    comp_lat = sum(comp_latencies) / len(comp_latencies)

    return EvalResult(
        compression_ratio=1 - (comp_tokens / max(orig_tokens, 1)),
        original_tokens=orig_tokens,
        compressed_tokens=comp_tokens,
        cost_reduction_pct=1 - (comp_cost / max(orig_cost, 1e-9)),
        original_cost_usd=orig_cost,
        compressed_cost_usd=comp_cost,
        reasoning_retention_score=sum(retention_scores) / len(retention_scores),
        original_latency_s=orig_lat,
        compressed_latency_s=comp_lat,
        latency_speedup_pct=1 - (comp_lat / max(orig_lat, 1e-9)),
    )


if __name__ == "__main__":
    # Quick manual smoke test - replace with real prompt + questions
    result = run_eval(
        original_prompt="...paste a long code/log context here...",
        compressed_prompt="...paste ZipPrompt output here...",
        eval_questions=["What does this code/log context describe?"],
    )
    print(asdict(result))
