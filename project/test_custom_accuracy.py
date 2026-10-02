"""
ZipPrompt Custom Accuracy Test Runner
Run live accuracy and compression tests on ANY custom Python code file or log file with custom questions.

Usage:
    python test_custom_accuracy.py --file path/to/your_file.py --query "Your question here"
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Ensure backend directory is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

load_dotenv()

from eval_harness import _count_tokens, _ask_llm, _answer_similarity
from ingestion import detect_domain
from custom_codecs.code_codec import build_code_graph
from custom_codecs.log_codec import build_log_templates
from query_router import rank_by_relevance
from budget_allocator import allocate_budget
from token_pruner import prune_tokens
from recovery_index import RecoveryIndex

def test_accuracy_on_custom_input(code_or_text: str, query: str, budget: int = 1000):
    print("\n" + "="*80)
    print(" [ZIPPROMPT ACCURACY TEST ON CUSTOM INPUT] ")
    print("="*80)
    
    orig_tokens = _count_tokens(code_or_text)
    print(f"\nOriginal Context Length: {orig_tokens} tokens")
    print(f"User Query: \"{query}\"")
    
    domain = detect_domain(code_or_text)
    print(f"Detected Domain: {domain.upper()}")
    
    if domain == "code":
        nodes = build_code_graph(code_or_text)
    else:
        nodes = build_log_templates(code_or_text)
        
    print(f"Parsed Total Nodes: {len(nodes)}")
    
    # Query router ranking
    ranked_nodes, confidence = rank_by_relevance(query, nodes)
    print(f"Relevance Router Confidence: {confidence:.4f}")
    
    # Budget allocation
    selected_nodes = []
    collapsed_nodes = []
    dropped_nodes = []
    running_tokens = 0
    
    recovery_idx = RecoveryIndex()
    session_id = "test_session"
    
    for n in ranked_nodes:
        if running_tokens + n.token_estimate <= budget:
            selected_nodes.append(n)
            running_tokens += n.token_estimate
        else:
            recovery_idx.store(session_id, n)
            stub_text = getattr(n, "stub", "")
            stub_estimate = len(stub_text.split()) if stub_text else 0
            if stub_text and (running_tokens + stub_estimate <= budget):
                collapsed_nodes.append(n)
                running_tokens += stub_estimate
            dropped_nodes.append(n.name)
            
    compressed_prompt = prune_tokens(selected_nodes, [], collapsed_nodes=collapsed_nodes)
    comp_tokens = _count_tokens(compressed_prompt)
    compression_ratio = (1.0 - (comp_tokens / max(orig_tokens, 1))) * 100
    
    print("\n" + "-"*80)
    print(" COMPRESSION METRICS")
    print("-"*80)
    print(f"  * Original Tokens   : {orig_tokens}")
    print(f"  * Compressed Tokens : {comp_tokens}")
    print(f"  * Token Savings     : {compression_ratio:.1f}%")
    print(f"  * Selected Nodes    : {[n.name for n in selected_nodes]}")
    print(f"  * Dropped Nodes     : {dropped_nodes}")
    
    print("\n" + "-"*80)
    print(" RUNNING LIVE MODEL EVALUATION (Gemini/Anthropic API)")
    print("-"*80)
    
    has_key = bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))
    if not has_key:
        print("Warning: No API key found. Running in mock mode. Add GOOGLE_API_KEY to project/.env for live API evaluation.")
        
    print("1. Querying model with FULL ORIGINAL context...")
    orig_answer, orig_time = _ask_llm(code_or_text, query, is_compressed=False)
    
    print("2. Querying model with COMPRESSED context...")
    comp_answer, comp_time = _ask_llm(compressed_prompt, query, is_compressed=True)
    
    similarity_score = _answer_similarity(orig_answer, comp_answer, query) * 100
    speedup = ((orig_time - comp_time) / max(orig_time, 1e-6)) * 100
    
    print("\n" + "="*80)
    print(" ACCURACY & ACCELERATION RESULTS")
    print("="*80)
    print(f"  * Reasoning Accuracy Retention : {similarity_score:.1f}%")
    print(f"  * Original Response Time      : {orig_time:.2f} seconds")
    print(f"  * Compressed Response Time    : {comp_time:.2f} seconds")
    print(f"  * Latency Speedup             : {speedup:.1f}%")
    
    print("\n" + "-"*80)
    print(" LLM ANSWERS COMPARISON")
    print("-"*80)
    print(f"[FULL CONTEXT ANSWER]:\n{orig_answer}\n")
    print(f"[COMPRESSED CONTEXT ANSWER]:\n{comp_answer}\n")
    print("="*80)
    
    return {
        "original_tokens": orig_tokens,
        "compressed_tokens": comp_tokens,
        "compression_ratio": compression_ratio,
        "accuracy_retention": similarity_score,
        "original_answer": orig_answer,
        "compressed_answer": comp_answer
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test ZipPrompt accuracy on custom code/files.")
    parser.add_argument("--file", type=str, help="Path to custom .py or .log file to test")
    parser.add_argument("--query", type=str, help="Question to ask about the code/file")
    parser.add_argument("--budget", type=int, default=1000, help="Target compressed token budget (default: 1000)")
    
    args = parser.parse_args()
    
    if args.file and args.query:
        with open(args.file, "r", encoding="utf-8") as f:
            code_text = f.read()
        test_accuracy_on_custom_input(code_text, args.query, args.budget)
    else:
        # Default fallback test on sample code with custom query
        sample_path = os.path.join(os.path.dirname(__file__), "data", "messy_sample.py")
        if os.path.exists(sample_path):
            with open(sample_path, "r", encoding="utf-8") as f:
                code_text = f.read()
            test_accuracy_on_custom_input(
                code_text, 
                query="How does password reset validation work and what tokens are generated?", 
                budget=800
            )
        else:
            print("Usage: python test_custom_accuracy.py --file path/to/file.py --query 'Your question'")
