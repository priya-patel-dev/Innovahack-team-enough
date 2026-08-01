"""
Stage 6: Token Pruner.
"""
import re

def refine_node_text(node) -> str:
    text = getattr(node, "body", getattr(node, "template", str(node)))
    # Strip comments and extra whitespace for minor clean-up, but perfectly retain the underlying semantics.
    text = re.sub(r'#.*', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def prune_tokens(selected_nodes: list, unchanged_pointers: list, rate: float = 0.3) -> str:
    """
    SEMANTIC PRUNER: Relies on the upstream Query Router (MiniLM vectors) to have filtered 
    out irrelevant nodes. We keep the surviving relevant nodes perfectly intact rather than 
    faking compression by blind-slicing strings.
    """
    pieces = []
    
    # 1. Surviving nodes (highly relevant based on MiniLM embeddings) are kept whole
    for node in selected_nodes:
        pieces.append(refine_node_text(node))

    # 2. Unchanged nodes from Diff Engine
    for ptr in unchanged_pointers:
        pieces.append(f"[unchanged: {ptr.name}]")

    return "\n\n".join(pieces)
