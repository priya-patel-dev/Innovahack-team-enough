"""
Test Query Router Ranking.
Verifies that TF-IDF relevance scoring with signature boosting and stemming
properly ranks context nodes.
"""
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from query_router import rank_by_relevance

class MockNode:
    def __init__(self, name: str, body: str, signature: str = "", docstring: str = ""):
        self.name = name
        self.body = body
        self.signature = signature
        self.docstring = docstring
        self.token_estimate = len(body.split())

def test_ranking_sanity():
    nodes = [
        MockNode("set_user_data_cache", "def set_user_data_cache(cache): self.user_data_cache = cache"),
        MockNode("get_is_active", "def get_is_active(): return self.is_active"),
        MockNode("calculate_complex_user_metrics", "def calculate_complex_user_metrics(user_id): return {'score': 100}"),
    ]

    # Query searching for metrics calculation logic
    query = "how does user metric scoring work?"
    
    ranked = rank_by_relevance(query, nodes)
    
    print("--- Ranked Nodes ---")
    for idx, n in enumerate(ranked):
        print(f"{idx+1}. {n.name}")

    # Assert calculate_complex_user_metrics is ranked 1st
    assert ranked[0].name == "calculate_complex_user_metrics"
    print("\nQuery Router Ranking Verification Test Passed successfully!")

if __name__ == "__main__":
    test_ranking_sanity()
