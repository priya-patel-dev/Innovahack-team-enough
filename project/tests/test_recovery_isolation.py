"""
Test Recovery Index Tenant Isolation & Storage.
Verifies:
1. Exact and semantic lookup within a session.
2. Cross-tenant isolation (Tenant B CANNOT access Tenant A's pruned code).
3. Tool definition schema structure.
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from recovery_index import RecoveryIndex


class DummyNode:
    def __init__(self, node_id: str, name: str, body: str):
        self.id = node_id
        self.name = name
        self.body = body
        self.kind = "code"


def test_recovery_tenant_isolation():
    idx = RecoveryIndex()

    node_tenant_a = DummyNode(
        "secret_algo_a",
        "proprietary_pricing_formula",
        "def proprietary_pricing_formula(): return 42"
    )
    node_tenant_b = DummyNode(
        "secret_algo_b",
        "billing_engine",
        "def billing_engine(): return 100"
    )

    # Store under tenant_a and tenant_b
    idx.store("session_1", node_tenant_a, tenant_id="tenant_a")
    idx.store("session_1", node_tenant_b, tenant_id="tenant_b")

    # Tenant A lookup succeeds for tenant A's node
    res_a = idx.lookup("session_1", "proprietary_pricing_formula", tenant_id="tenant_a")
    assert res_a["found"] is True
    assert "return 42" in res_a["items"][0]["content"]
    assert "return 42" in res_a["results"]["documents"][0][0]

    # Tenant B lookup for Tenant A's secret MUST FAIL (No data leakage!)
    res_b_attempt = idx.lookup("session_1", "proprietary_pricing_formula", tenant_id="tenant_b")
    assert res_b_attempt["found"] is False


def test_agent_tool_spec():
    spec = RecoveryIndex.get_tool_spec()
    assert spec["name"] == "recover_pruned_context"
    assert "node_id" in spec["parameters"]["properties"]
