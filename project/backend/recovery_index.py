"""
Stage 7: Recovery Index.

Content that got cut for budget reasons isn't lost - it's embedded and
stored here, keyed by session. If the target LLM's answer signals it's
missing something ("I don't have enough information about X"), a cheap
lookup pulls the dropped chunk back and triggers a single re-query.

Uses chromadb in ephemeral (in-memory) mode - zero setup for a demo.
"""
import chromadb


class RecoveryIndex:
    def __init__(self):
        self._client = chromadb.Client()  # in-memory, resets on restart
        self._collections: dict[str, "chromadb.Collection"] = {}

    def _collection_for(self, session_id: str):
        if session_id not in self._collections:
            self._collections[session_id] = self._client.create_collection(
                name=f"session_{session_id}"
            )
        return self._collections[session_id]

    def store(self, session_id: str, node) -> None:
        coll = self._collection_for(session_id)
        text = getattr(node, "body", None) or getattr(node, "template", "") or str(node)
        coll.add(
            documents=[text],
            ids=[node.id],
            metadatas=[{"name": getattr(node, "name", node.id)}],
        )

    def lookup(self, session_id: str, query: str, n_results: int = 1):
        coll = self._collection_for(session_id)
        if coll.count() == 0:
            return {"found": False, "results": []}
        results = coll.query(query_texts=[query], n_results=n_results)
        return {"found": True, "results": results}
