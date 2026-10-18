"""
Stage 3: Diff Engine.

Maintains session-aware hashing state across conversational turns.
Ensures repeat requests in a multi-turn session only pay for changed components.
Unchanged components are collapsed to lightweight pointers.

Features:
- Multi-tenant isolation: (tenant_id, session_id)
- Thread-safe concurrency via RLock
- LRU cache eviction to prevent memory leaks in production
"""
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass
class Pointer:
    """Lightweight reference to a node that hasn't changed since last turn."""
    id: str
    name: str


class SessionCache:
    def __init__(self, max_sessions: int = 5000):
        self._max_sessions = max_sessions
        # key: (tenant_id, session_id) -> dict[node_id, content_hash]
        self._hashes: OrderedDict[tuple[str, str], dict[str, str]] = OrderedDict()
        self._lock = threading.RLock()

    def _get_key(self, session_id: str, tenant_id: str = "default") -> tuple[str, str]:
        return (tenant_id or "default", session_id)

    def diff(self, session_id: str, nodes: list[Any], tenant_id: str = "default") -> tuple[list[Any], list[Pointer]]:
        """
        Calculates delta between incoming nodes and cached session state.
        Returns:
            (new_or_changed_nodes, unchanged_pointers)
        """
        key = self._get_key(session_id, tenant_id)
        with self._lock:
            prev = self._hashes.get(key, {})
            # Touch key for LRU
            if key in self._hashes:
                self._hashes.move_to_end(key)

            new_or_changed = []
            unchanged = []

            for node in nodes:
                h = node.content_hash()
                if prev.get(node.id) == h:
                    unchanged.append(Pointer(id=node.id, name=getattr(node, "name", node.id)))
                else:
                    new_or_changed.append(node)

            return new_or_changed, unchanged

    def commit(self, session_id: str, nodes: list[Any], tenant_id: str = "default") -> None:
        """Commits the latest node snapshot for the session."""
        key = self._get_key(session_id, tenant_id)
        with self._lock:
            self._hashes[key] = {n.id: n.content_hash() for n in nodes}
            self._hashes.move_to_end(key)

            # Evict oldest sessions if exceeding max limit
            while len(self._hashes) > self._max_sessions:
                self._hashes.popitem(last=False)

    def clear(self, session_id: str, tenant_id: str = "default") -> bool:
        """Clear session cache for a tenant session."""
        key = self._get_key(session_id, tenant_id)
        with self._lock:
            if key in self._hashes:
                del self._hashes[key]
                return True
            return False
