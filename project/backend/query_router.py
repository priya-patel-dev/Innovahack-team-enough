"""
Stage 4: Query Router.

Ranks structural nodes by relevance to the live query using a small
local embedding model. This is what makes compression query-aware
instead of static - the same context compresses differently depending
on what's being asked.
"""
from functools import lru_cache

from sentence_transformers import SentenceTransformer
import numpy as np


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    # Loaded once and cached; MiniLM is small enough to run on CPU fast.
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def _node_text(node) -> str:
    if hasattr(node, "signature"):  # CodeNode
        return f"{node.signature}\n{node.docstring}"
    if hasattr(node, "template"):  # LogNode
        return node.template
    return getattr(node, "name", str(node))


def rank_by_relevance(query: str, nodes: list) -> list:
    if not nodes:
        return []

    model = _get_model()
    node_texts = [_node_text(n) for n in nodes]

    query_vec = model.encode([query])[0]
    node_vecs = model.encode(node_texts)

    sims = node_vecs @ query_vec / (
        np.linalg.norm(node_vecs, axis=1) * np.linalg.norm(query_vec) + 1e-8
    )

    ranked = [n for _, n in sorted(zip(sims, nodes), key=lambda x: -x[0])]
    return ranked
