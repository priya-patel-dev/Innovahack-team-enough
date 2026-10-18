"""
Test FastAPI Endpoints.
Verifies:
1. /health returns healthy status
2. /compress successfully processes code context and produces valid response
3. /recover returns recovered node
4. /tool-schema returns agent tool definition
5. Error validation on empty inputs
"""
import os
import sys
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_tool_schema_endpoint():
    response = client.get("/tool-schema")
    assert response.status_code == 200
    assert "recover_pruned_context" in response.json()["name"]


def test_compress_endpoint_valid():
    payload = {
        "session_id": "test_api_session",
        "tenant_id": "test_tenant",
        "query": "how does the auth service validate users?",
        "context": """
import sys

def validate_auth_token(token: str) -> bool:
    \"\"\"Checks validity of access token.\"\"\"
    return token.startswith('bearer_')

def calculate_hash(password: str) -> str:
    \"\"\"Computes password hash.\"\"\"
    return 'hashed_' + password
""",
        "cost_pressure": 0.5,
        "latency_pressure": 0.5
    }
    response = client.post("/compress", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "compressed_prompt" in data
    assert data["original_tokens"] > 0
    assert data["compressed_tokens"] > 0
    assert data["domain"] == "code"


def test_compress_endpoint_empty_input():
    response = client.post("/compress", json={"session_id": "s1", "query": "", "context": ""})
    assert response.status_code in (400, 422)


def test_recover_endpoint_query_params_and_body():
    # 1. Compress a context with tight budget to force dropping
    payload = {
        "session_id": "session_rec_test",
        "tenant_id": "tenant_rec_test",
        "query": "validate_auth_token",
        "context": """
def validate_auth_token(token: str) -> bool:
    return True

def unused_large_service():
    return 'very long string that gets dropped when budget is tiny'
""",
        "target_tokens": 10
    }
    res_comp = client.post("/compress", json=payload)
    assert res_comp.status_code == 200

    # 2. Test query parameter style (frontend console / streamlit)
    res_qp = client.post(
        "/recover?session_id=session_rec_test&missing_entity=unused_large_service&tenant_id=tenant_rec_test"
    )
    assert res_qp.status_code == 200
    data_qp = res_qp.json()
    assert data_qp["found"] is True

    # 3. Test JSON body style (agentic tool call)
    res_body = client.post(
        "/recover",
        json={
            "session_id": "session_rec_test",
            "query_or_node_id": "unused_large_service",
            "tenant_id": "tenant_rec_test"
        }
    )
    assert res_body.status_code == 200
    data_body = res_body.json()
    assert data_body["found"] is True
