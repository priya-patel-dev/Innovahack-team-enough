"""
Stage 6: Token Pruner.

Fine-grained cleanup applied ONLY to nodes that survived structural
conversion + query routing + budgeting. Deliberately the last and
smallest stage - most teams make this the whole project; here it's
just cleanup on top of the bigger structural/routing wins.
"""
from functools import lru_cache

from llmlingua import PromptCompressor


@lru_cache(maxsize=1)
def _get_compressor() -> PromptCompressor:
    return PromptCompressor(model_name="microsoft/llmlingua-2-xlm-roberta-large-meetingbank")


def _node_to_text(node) -> str:
    if hasattr(node, "body"):  # CodeNode
        return f"{node.signature}\n{node.docstring}\n{node.body}"
    if hasattr(node, "template"):  # LogNode
        sample = "\n".join(node.sample_lines)
        return f"{node.template} (x{node.count})\n{sample}"
    return getattr(node, "name", str(node))


def prune_tokens(selected_nodes: list, unchanged_pointers: list, rate: float = 0.5) -> str:
    """
    Runs llmlingua-style compression on surviving nodes, then appends
    lightweight references for nodes unchanged since last turn (diff
    engine output) so the target LLM knows they still exist without
    re-sending their full content.
    """
    compressor = _get_compressor()
    pieces = []

    for node in selected_nodes:
        text = _node_to_text(node)
        try:
            result = compressor.compress_prompt(text, rate=rate)
            pieces.append(result["compressed_prompt"])
        except Exception:
            # Fail open: if llmlingua chokes on this node, keep it raw
            # rather than dropping content silently.
            pieces.append(text)

    for ptr in unchanged_pointers:
        pieces.append(f"[unchanged: {ptr.name}]")

    return "\n\n".join(pieces)
