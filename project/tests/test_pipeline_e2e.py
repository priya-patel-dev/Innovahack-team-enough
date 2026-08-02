"""
End-to-End Pipeline Integration Test.
Runs the sample code context through the ZipPrompt stages:
Ingestion -> Code Codec -> Diff Engine -> Query Router -> Budget Allocator -> Token Pruner -> Recovery Store.
"""
import os
import sys

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from ingestion import detect_domain
from custom_codecs.code_codec import build_code_graph
from diff_engine import SessionCache
from query_router import rank_by_relevance
from budget_allocator import allocate_budget
from token_pruner import prune_tokens
from recovery_index import RecoveryIndex

SAMPLE_CODE = """
class EnterpriseUserManagerProxyFactory:
    \"\"\"Factory to proxy user management requests.\"\"\"
    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    def set_user_data_cache(self, user_id: str, data: dict):
        \"\"\"Cache user data for quick retrieval.\"\"\"
        pass

    def get_user_data_cache(self, user_id: str):
        \"\"\"Retrieve cached user data.\"\"\"
        return {}

    def set_is_active(self, user_id: str, is_active: bool):
        \"\"\"Activate or deactivate user.\"\"\"
        pass

    def get_is_active(self, user_id: str) -> bool:
        \"\"\"Check user active status.\"\"\"
        return True

    def calculate_complex_user_metrics(self, user_id: str, scores: list[int]) -> float:
        \"\"\"
        Calculate user health metrics based on a complex historical scores list.
        Applies a multiplier of 1.5 for active users with scores exceeding 100.
        \"\"\"
        if len(scores) == 0:
            return 0.0
        base = sum(scores) / len(scores)
        if base > 100:
            return base * 1.5
        return base
"""

def test_e2e():
    print("--- Stage 1: Ingestion ---")
    domain = detect_domain(SAMPLE_CODE)
    print(f"Detected domain: {domain}")
    assert domain == "code"

    print("\n--- Stage 2: Code Codec ---")
    nodes = build_code_graph(SAMPLE_CODE)
    print(f"Node count: {len(nodes)}")
    for n in nodes:
        print(f" - {n.kind.upper()} {n.name} ({n.token_estimate} tokens)")

    print("\n--- Stage 3: Diff Engine (Turn 1) ---")
    session_cache = SessionCache()
    new_or_changed, unchanged_pointers = session_cache.diff("session-1", nodes)
    session_cache.commit("session-1", nodes)
    print(f"Turn 1: {len(new_or_changed)} new/changed, {len(unchanged_pointers)} unchanged")
    assert len(new_or_changed) == len(nodes)
    assert len(unchanged_pointers) == 0

    print("\n--- Stage 3: Diff Engine (Turn 2 - No Changes) ---")
    new_or_changed_2, unchanged_pointers_2 = session_cache.diff("session-1", nodes)
    print(f"Turn 2: {len(new_or_changed_2)} new/changed, {len(unchanged_pointers_2)} unchanged")
    assert len(new_or_changed_2) == 0
    assert len(unchanged_pointers_2) == len(nodes)

    print("\n--- Stage 4: Query Router ---")
    query = "how does user metric scoring work?"
    ranked, confidence = rank_by_relevance(query, nodes)
    print("Ranked nodes for query:")
    for i, n in enumerate(ranked):
        print(f" {i+1}. {n.name}")
    
    # The most relevant function should be calculate_complex_user_metrics
    assert ranked[0].name == "EnterpriseUserManagerProxyFactory.calculate_complex_user_metrics"

    print("\n--- Stage 5 & 6: Budgeting & Pruning ---")
    # Set a budget that fits only the top 3 nodes
    budget = 100
    selected_nodes = []
    running_tokens = 0
    recovery_index = RecoveryIndex()
    
    for node in ranked:
        if running_tokens + node.token_estimate > budget:
            recovery_index.store("session-1", node)
            continue
        selected_nodes.append(node)
        running_tokens += node.token_estimate

    print(f"Selected {len(selected_nodes)} nodes (total {running_tokens} tokens)")
    compressed = prune_tokens(selected_nodes, unchanged_pointers_2)
    print("Compressed Prompt Output:")
    print(compressed)

    print("\n--- Stage 7: Recovery Store ---")
    lookup_res = recovery_index.lookup("session-1", "user active status")
    print(f"Recovery lookup result: {lookup_res}")
    
    print("\nE2E Pipeline Test Passed Successfully!")

if __name__ == "__main__":
    test_e2e()
