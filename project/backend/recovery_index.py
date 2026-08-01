"""
Stage 7: Recovery Index.

Content that got cut for budget reasons isn't lost - it's embedded and
stored here, keyed by session. If the target LLM's answer signals it's
missing something ("I don't have enough information about X"), a cheap
lookup pulls the dropped chunk back and triggers a single re-query.

Uses chromadb in ephemeral (in-memory) mode - zero setup for a demo.
"""
class RecoveryIndex:
    def __init__(self):
        # session_id -> list of dicts {"id": str, "name": str, "text": str}
        self._store: dict[str, list[dict]] = {}

    def store(self, session_id: str, node) -> None:
        if session_id not in self._store:
            self._store[session_id] = []
            
        text = getattr(node, "body", None) or getattr(node, "template", "") or str(node)
        self._store[session_id].append({
            "id": node.id,
            "name": getattr(node, "name", node.id),
            "text": text
        })

    def lookup(self, session_id: str, query: str, n_results: int = 1):
        """Simple substring matching instead of vector similarity to reduce risk."""
        if session_id not in self._store or not self._store[session_id]:
            return {"found": False, "results": []}
            
        # Trivial scoring based on token overlap or just simple 'in'
        query_terms = query.lower().split()
        
        def score(doc):
            text_lower = doc["text"].lower()
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
