"""
Stage 7: Recovery Index.

Content that got cut for budget reasons is stored in an in-memory dictionary.
A lightweight keyword-overlap scorer searches stored chunks and pulls the
most relevant one back on demand. Zero dependencies, CPU-only.
"""
import re

class RecoveryIndex:
    def __init__(self):
        # session_id -> list of dicts {"id": str, "name": str, "text": str}
        self._store: dict[str, list[dict]] = {}

    def store(self, session_id: str, node) -> None:
        if session_id not in self._store:
            self._store[session_id] = []
            
        text = getattr(node, "body", None) or getattr(node, "template", "") or str(node)
        
        # Check if already stored to avoid duplicates
        if not any(item["id"] == node.id for item in self._store[session_id]):
            self._store[session_id].append({
                "id": node.id,
                "name": getattr(node, "name", node.id),
                "text": text
            })

    def lookup(self, session_id: str, query: str, n_results: int = 1):
        """Simple substring matching instead of vector similarity to reduce risk."""
        if session_id not in self._store or not self._store[session_id]:
            return {"found": False, "results": []}
            
        query_terms = query.lower().split()
        
        def score(doc):
            text_lower = (doc["name"] + " " + doc["text"]).lower()
            return sum(1 for term in query_terms if term in text_lower)
            
        ranked = sorted(self._store[session_id], key=score, reverse=True)
        # Only return results that have at least some overlap
        best = [r for r in ranked if score(r) > 0][:n_results]
        
        if not best:
            return {"found": False, "results": []}
            
        # Format similar to how chromadb would return
        return {
            "found": True, 
            "results": {
                "ids": [[b["id"] for b in best]],
                "documents": [[b["text"] for b in best]],
                "metadatas": [[{"name": b["name"]} for b in best]]
            }
        }
