import requests
from sentence_transformers import SentenceTransformer
import numpy as np
import os

def run_evals():
    print("====== ZipPrompt Semantic Eval Suite ======")
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    
    with open(os.path.join("..", "data", "messy_auth.py"), "r") as f:
        auth_code = f.read()

    test_cases = [
        ("How do I validate the session token?", "validate_session_token_for_incoming_request Validates the session token for the user request"),
        ("How do I authenticate a user?", "hashes the password securely using SHA-256 and compares it against the secure database"),
        ("What happens to the token when I logout?", "logout_user_and_securely_destroy_session physically removes the session token from the active cache"),
        ("How do I refresh a session?", "refresh_user_session_token_if_needed Refreshes the backend user session token if it is set to expire")
    ]
    
    total_compression = []
    semantic_retention = []

    print("\n--- Running 4-Case Matrix ---")
    for query, expected_meaning in test_cases:
        print(f"\n[Test] Query: '{query}'")
        
        # Uncompressed Baseline Semantic Score
        uncompressed_vec = model.encode([auth_code])[0]
        expected_vec = model.encode([expected_meaning])[0]
        baseline_score = np.dot(uncompressed_vec, expected_vec) / (np.linalg.norm(uncompressed_vec) * np.linalg.norm(expected_vec) + 1e-8)
        
        # Run Compression Route
        r = requests.post("http://localhost:8000/compress", json={
            "session_id": "eval-run-" + query[:5],
            "query": query,
            "context": auth_code,
            "cost_pressure": 0.5,
            "latency_pressure": 0.5
        })
        data = r.json()
        compressed_text = data["compressed_prompt"]
        comp_ratio = data["compression_ratio"]
        total_compression.append(comp_ratio)
        
        # Compressed Semantic Score
        compressed_vec = model.encode([compressed_text])[0]
        compressed_score = np.dot(compressed_vec, expected_vec) / (np.linalg.norm(compressed_vec) * np.linalg.norm(expected_vec) + 1e-8)
        
        # Relative retention
        retention = min(1.0, compressed_score / baseline_score) if baseline_score > 0 else 0
        semantic_retention.append(retention)
        
        print(f"  -> Compression Ratio: {comp_ratio*100:.1f}%")
        print(f"  -> Semantic Retention Score: {retention*100:.1f}%")

    print("\n--- Validating Metric Sensitivity (Negative Control) ---")
    # Deliberately feed a 'Near Miss' code block (wrong auth function) to prove metric precision
    print("[Test] Negative Control 'Near Miss': Passing a plausible but incorrect Auth function")
    # Simulate a pipeline failure: The question asks about Validating Token, but we pass Refresh Token logic
    near_miss_context = "def refresh_user_session_token_if_needed(self, current_token):\n    pass\n    # Refreshes the backend user session"
    near_miss_vec = model.encode([near_miss_context])[0]
    
    # We are asking about 'Validate Token', which is index 0
    expected_mc_vec = model.encode([test_cases[0][1]])[0] 
    
    near_miss_score = np.dot(near_miss_vec, expected_mc_vec) / (np.linalg.norm(near_miss_vec) * np.linalg.norm(expected_mc_vec) + 1e-8)
    uncomp_mc_vec = model.encode([auth_code])[0]
    base_mc_score = np.dot(uncomp_mc_vec, expected_mc_vec) / (np.linalg.norm(uncomp_mc_vec) * np.linalg.norm(expected_mc_vec) + 1e-8)
    
    retention_drop = min(1.0, near_miss_score / base_mc_score) if base_mc_score > 0 else 0
    print(f"  -> When a Near-Miss Auth function is returned instead, Metric Drops To: {retention_drop*100:.1f}%")

    if retention_drop < 0.85:
         print("  -> NEGATIVE CONTROL PASSED: The metric catches fine-grained logical destruction, not just wildly unrelated garbage.")

    print("\n====== Final Pipeline Metrics ======")
    print(f"Avg Compression: {np.mean(total_compression)*100:.1f}%")
    print(f"Avg Accuracy Retention: {np.mean(semantic_retention)*100:.1f}%")

if __name__ == "__main__":
    run_evals()
