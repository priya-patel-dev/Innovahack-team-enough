"""
Test Diff Engine Turn Caching.
Verifies that unchanged nodes collapse to pointer references on subsequent turns,
answering Differentiator #3.
"""
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from diff_engine import SessionCache

class MockNode:
    def __init__(self, node_id: str, name: str, body: str):
        self.id = node_id
        self.name = name
        self.body = body

    def content_hash(self) -> str:
        import hashlib
        return hashlib.sha256(self.body.encode()).hexdigest()

def test_session_diff():
    session_id = "test-session-diff-1"
    cache = SessionCache()

    # Turn 1: 3 nodes
    nodes_turn1 = [
        MockNode("node_1", "setup_config", "def setup_config(): pass"),
        MockNode("node_2", "run_server", "def run_server(): print('running')"),
        MockNode("node_3", "stop_server", "def stop_server(): print('stopped')"),
    ]

    new_or_changed, unchanged_pointers = cache.diff(session_id, nodes_turn1)
    cache.commit(session_id, nodes_turn1)

    print("--- Turn 1 ---")
    print(f"New/Changed nodes: {[n.name for n in new_or_changed]}")
    print(f"Unchanged pointers: {[p.name for p in unchanged_pointers]}")

    assert len(new_or_changed) == 3
    assert len(unchanged_pointers) == 0

    # Turn 2: Node 2 changes, Node 1 & 3 remain same
    nodes_turn2 = [
        MockNode("node_1", "setup_config", "def setup_config(): pass"),
        MockNode("node_2", "run_server", "def run_server(): print('v2 modified')"),  # modified!
        MockNode("node_3", "stop_server", "def stop_server(): print('stopped')"),
    ]

    new_or_changed_2, unchanged_pointers_2 = cache.diff(session_id, nodes_turn2)
    cache.commit(session_id, nodes_turn2)

    print("\n--- Turn 2 ---")
    print(f"New/Changed nodes: {[n.name for n in new_or_changed_2]}")
    print(f"Unchanged pointers: {[p.name for p in unchanged_pointers_2]}")

    # Assertions
    assert len(new_or_changed_2) == 1
    assert new_or_changed_2[0].id == "node_2"
    
    assert len(unchanged_pointers_2) == 2
    assert {p.id for p in unchanged_pointers_2} == {"node_1", "node_3"}

    print("\nDiff Engine Verification Test Passed successfully!")

if __name__ == "__main__":
    test_session_diff()
