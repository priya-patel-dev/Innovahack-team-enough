"""
Stage 7: Recovery Index.

Stores dropped context nodes in a compressed in-memory store so any pruned
data can be retrieved on-demand if the downstream LLM or user requires it.

Features:
- Strict tenant and session isolation (prevents cross-session data leakage)
- Thread-safe access via RLock
- zlib compression of stored payloads for low memory footprint
- Fast keyword + exact-match retrieval
- Exportable Agentic Tool Schema for Claude/OpenAI/Gemini function calling
- Dual response format: structured items + chromadb/streamlit compatible dictionaries
"""
import re
import zlib
import threading
from collections import OrderedDict
from typing import Any, Optional


class RecoveryIndex:
    def __init__(self, max_sessions: int = 5000, max_items_per_session: int = 500):
        self._max_sessions = max_sessions
        self._max_items_per_session = max_items_per_session
        # key: (tenant_id, session_id) -> list of dicts {"id": str, "name": str, "text": bytes, "kind": str}
        self._store: OrderedDict[tuple[str, str], list[dict[str, Any]]] = OrderedDict()
        self._lock = threading.RLock()

    def _get_key(self, session_id: str, tenant_id: str = "default") -> tuple[str, str]:
        return (tenant_id or "default", session_id)

    def store(self, session_id: str, node: Any, tenant_id: str = "default") -> None:
        """Stores a pruned node into the recovery index under strict tenant/session isolation."""
        key = self._get_key(session_id, tenant_id)
        text = getattr(node, "body", None) or getattr(node, "template", "") or str(node)
        node_id = getattr(node, "id", str(node))
        node_name = getattr(node, "name", node_id)
        node_kind = getattr(node, "kind", "code")

        with self._lock:
            if key not in self._store:
                self._store[key] = []
            
            # Touch key for LRU
            self._store.move_to_end(key)
            session_items = self._store[key]

            # Avoid storing exact duplicate node IDs
            for item in session_items:
                if item["id"] == node_id:
                    return

            compressed_text = zlib.compress(text.encode("utf-8"))
            session_items.append({
                "id": node_id,
                "name": node_name,
                "kind": node_kind,
                "text": compressed_text
            })

            # Enforce max items per session
            if len(session_items) > self._max_items_per_session:
                session_items.pop(0)

            # Enforce max sessions across memory
            while len(self._store) > self._max_sessions:
                self._store.popitem(last=False)

    def lookup(
        self,
        session_id: str,
        query: str,
        tenant_id: str = "default",
        n_results: int = 1
    ) -> dict[str, Any]:
        """
        Retrieves matching dropped nodes for a given query or exact node_id.
        Strictly isolated to the specified tenant_id and session_id.
        """
        key = self._get_key(session_id, tenant_id)
        with self._lock:
            candidates = self._store.get(key, [])
            if not candidates:
                return {
                    "found": False,
                    "session_id": session_id,
                    "items": [],
                    "results": {"ids": [[]], "documents": [[]], "metadatas": [[]]},
                    "message": f"No recovery items stored for session '{session_id}'."
                }

        query_raw = (query or "").strip()
        query_lower = query_raw.lower()

        # 1. First check if query is an exact node ID
        for item in candidates:
            if item["id"].lower() == query_lower or item["name"].lower() == query_lower:
                decompressed = zlib.decompress(item["text"]).decode("utf-8")
                return {
                    "found": True,
                    "session_id": session_id,
                    "items": [{
                        "id": item["id"],
                        "name": item["name"],
                        "kind": item["kind"],
                        "content": decompressed,
                        "score": 100.0
                    }],
                    "results": {
                        "ids": [[item["id"]]],
                        "documents": [[decompressed]],
                        "metadatas": [[{"name": item["name"], "kind": item["kind"]}]]
                    }
                }

        # 2. Tokenized & CamelCase keyword matching
        words = re.findall(r'[a-zA-Z0-9_]+', query_lower)
        camel_split = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', query_raw).lower().split()
        search_terms = set(words + camel_split)

        scored: list[tuple[dict[str, Any], float]] = []
        for doc in candidates:
            decompressed = zlib.decompress(doc["text"]).decode("utf-8")
            doc_name = doc["name"].lower()
            doc_id = doc["id"].lower()
            text_lower = (doc_name + " " + doc_id + " " + decompressed).lower()

            score = 0.0
            if query_lower in doc_name or query_lower in doc_id:
                score += 50.0

            for term in search_terms:
                if len(term) >= 2:
                    if term in doc_name:
                        score += 15.0
                    elif term in text_lower:
                        score += 5.0

            if score > 0:
                scored.append((doc, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        best = scored[:n_results]

        if not best:
            return {
                "found": False,
                "session_id": session_id,
                "items": [],
                "results": {"ids": [[]], "documents": [[]], "metadatas": [[]]},
                "message": f"No recovered nodes matched query '{query}'."
            }

        items = []
        ids = []
        docs = []
        metas = []

        for doc, sc in best:
            decompressed = zlib.decompress(doc["text"]).decode("utf-8")
            items.append({
                "id": doc["id"],
                "name": doc["name"],
                "kind": doc["kind"],
                "content": decompressed,
                "score": sc
            })
            ids.append(doc["id"])
            docs.append(decompressed)
            metas.append({"name": doc["name"], "kind": doc["kind"]})

        return {
            "found": True,
            "session_id": session_id,
            "items": items,
            "results": {
                "ids": [ids],
                "documents": [docs],
                "metadatas": [metas]
            }
        }

    @staticmethod
    def get_tool_spec() -> dict[str, Any]:
        """Returns JSON Schema for agentic tool calling with LLMs."""
        return {
            "name": "recover_pruned_context",
            "description": "Retrieves the full source code or log details of a collapsed or pruned node.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "The exact node identifier (e.g. 'method:Class.func_name') or semantic search keyword."
                    }
                },
                "required": ["node_id"]
            }
        }
