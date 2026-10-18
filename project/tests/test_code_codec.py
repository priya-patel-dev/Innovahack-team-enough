"""
Test AST Code Codec.
Verifies:
1. Extraction of imports, classes, methods, functions.
2. Reconstructed code is 100% syntactically valid and parses with ast.parse().
3. Collapsed methods are formatted as valid Python ellipsis stubs with proper indentation.
"""
import ast
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from custom_codecs.code_codec import build_code_graph, render_compressed_code


SAMPLE_SOURCE = """
import os
import sys
from typing import Optional

GLOBAL_TIMEOUT: int = 30
API_VERSION = "2.0.0"

def helper_function(x: int) -> int:
    \"\"\"Doubles an integer.\"\"\"
    return x * 2

class UserAccountManager:
    \"\"\"Manages user login and session states.\"\"\"
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.is_connected = False

    def connect(self) -> bool:
        \"\"\"Establish database connection.\"\"\"
        self.is_connected = True
        return True

    def calculate_risk(self, user_id: str, balance: float) -> float:
        \"\"\"Computes transaction risk score.\"\"\"
        if balance < 0:
            return 1.0
        return 0.1
"""


def test_code_codec_parsing():
    nodes = build_code_graph(SAMPLE_SOURCE)
    node_names = [n.name for n in nodes]
    node_kinds = [n.kind for n in nodes]

    # Verify imports captured
    assert "module_imports" in node_names
    assert "import" in node_kinds

    # Verify class & methods
    assert "UserAccountManager" in node_names
    assert "UserAccountManager.__init__" in node_names
    assert "UserAccountManager.connect" in node_names
    assert "UserAccountManager.calculate_risk" in node_names
    assert "helper_function" in node_names


def test_code_codec_valid_reconstruction():
    nodes = build_code_graph(SAMPLE_SOURCE)
    
    # Select only imports, class header, and calculate_risk
    # Collapse connect and __init__
    selected_ids = {
        "imports:module",
        "class:UserAccountManager",
        "method:UserAccountManager.calculate_risk"
    }
    collapsed_ids = {
        "method:UserAccountManager.__init__",
        "method:UserAccountManager.connect",
        "func:helper_function"
    }

    reconstructed = render_compressed_code(nodes, selected_ids, collapsed_ids)

    # CRITICAL TEST: Must be 100% valid Python!
    parsed_tree = ast.parse(reconstructed)
    assert parsed_tree is not None

    # Verify unselected connect method is collapsed
    assert "def calculate_risk" in reconstructed
    assert "return 1.0" in reconstructed
    assert "def connect" in reconstructed
    assert "# [collapsed: node 'method:UserAccountManager.connect']" in reconstructed
