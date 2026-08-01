"""
Stage 3: Diff Engine.

Maintains per-session state so repeat turns only pay for what changed.
This is the piece that directly answers the "real-time interactions"
pain point from the problem statement - most teams treat this as a
single-shot prompt problem and skip session state entirely.

Swap the in-memory dict for SQLite/Redis if you need persistence across
backend restarts during the demo; in-memory is fine for a hackathon.
"""
from dataclasses import dataclass


@dataclass
class Pointer:
    """Lightweight reference to a node that hasn't changed since last turn."""
    id: str
    name: str


class SessionCache:
    def __init__(self):
        # session_id -> {node_id: content_hash}
        self._hashes: dict[str, dict[str, str]] = {}

    def diff(self, session_id: str, nodes: list) -> tuple[list, list[Pointer]]:
        """
        Returns (new_or_changed_nodes, unchanged_pointers).
        `nodes` must expose .id and .content_hash().
        """
        prev = self._hashes.get(session_id, {})
        new_or_changed = []
        unchanged = []

        for node in nodes:
            h = node.content_hash()
            if prev.get(node.id) == h:
                unchanged.append(Pointer(id=node.id, name=getattr(node, "name", node.id)))
            else:
                new_or_changed.append(node)

        return new_or_changed, unchanged

    def commit(self, session_id: str, nodes: list) -> None:
        """Call after a successful compress() to update the session snapshot."""
        self._hashes[session_id] = {n.id: n.content_hash() for n in nodes}
