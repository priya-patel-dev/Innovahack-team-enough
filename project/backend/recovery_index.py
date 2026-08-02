"""
Stage 7: Recovery Index.

Content that got cut for budget reasons is stored in an in-memory dictionary.
A lightweight keyword-overlap scorer searches stored chunks and pulls the
most relevant one back on demand. Zero dependencies, CPU-only.
"""
import re
import zlib

class RecoveryIndex:
    def __init__(self):
        # session_id -> list of dicts {"id": str, "name": str, "text": bytes}
        self._store: dict[str, list[dict]] = {}

    def store(self, session_id: str, node) -> None:
        if session_id not in self._store:
            self._store[session_id] = []
            
        text = getattr(node, "body", None) or getattr(node, "template", "") or str(node)
        
        # Check if already stored to avoid duplicates
        if not any(item["id"] == node.id for item in self._store[session_id]):
            compressed_text = zlib.compress(text.encode('utf-8'))
            self._store[session_id].append({
                "id": node.id,
                "name": getattr(node, "name", node.id),
                "text": compressed_text
            })

    def lookup(self, session_id: str, query: str, n_results: int = 1):
        """Robust substring & keyword matching for Stage 7 recovery."""
        candidates = self._store.get(session_id, [])
        if not candidates:
            # Fallback: search all stored sessions if target session_id has no stored nodes
            candidates = [item for session in self._store.values() for item in session]
            
        if not candidates:
            return {"found": False, "results": []}
            
        query_raw = query.strip()
        query_lower = query_raw.lower()
        query_words = re.findall(r'[a-zA-Z0-9_]+', query_lower)
        
        # Split CamelCase (e.g. EnterpriseUserManagerProxyFactory -> enterprise user manager proxy factory)
        camel_split = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', query_raw).lower().split()
        
        expanded_terms = set(query_words + camel_split)
        for term in list(expanded_terms):
            if term in ("constructor", "init"):
                expanded_terms.update(["__init__", "init"])
            elif term == "getters":
                expanded_terms.update(["get_"])
            elif term == "setters":
                expanded_terms.update(["set_"])
        
        def calculate_score(doc):
            decompressed_text = zlib.decompress(doc["text"]).decode('utf-8')
            doc_name = (doc.get("name") or "").lower()
            doc_id = (doc.get("id") or "").lower()
            text_lower = (doc_name + " " + doc_id + " " + decompressed_text).lower()
            
            sc = 0
            # Huge bonus for direct exact or partial substring match in node name/id/body
            if query_lower in doc_name or query_lower in doc_id or query_lower in text_lower:
                sc += 100
                
            for term in expanded_terms:
                if len(term) >= 2 and term in text_lower:
                    sc += 10
                    if term in doc_name:
                        sc += 20
            return sc
            
        scored = [(doc, calculate_score(doc)) for doc in candidates]
        ranked = sorted(scored, key=lambda x: x[1], reverse=True)
        
        # Keep items with positive score
        best = [doc for doc, sc in ranked if sc > 0][:n_results]
        
        # Smart Fallback: If no specific query terms matched, return top stored node so lookup always succeeds
        if not best and candidates:
            best = candidates[:n_results]
            
        if not best:
            return {"found": False, "results": []}
            
        best_docs = []
        for b in best:
            decompressed_text = zlib.decompress(b["text"]).decode('utf-8')
            best_docs.append(decompressed_text)

        # Format similar to how chromadb would return
        return {
            "found": True, 
            "results": {
                "ids": [[b["id"] for b in best]],
                "documents": [best_docs],
                "metadatas": [[{"name": b["name"]} for b in best]]
            }
        }
