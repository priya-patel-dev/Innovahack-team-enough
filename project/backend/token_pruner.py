"""
Stage 6: Token Pruner.

Assembles and formats compressed prompts from:
1. Selected nodes (full implementation)
2. Collapsed nodes (syntactic stubs with signatures & docstrings)
3. Unchanged session pointers (cached session references)

Ensures that code is syntactically sound and passes ast.parse().
"""
from typing import Any, Optional
from custom_codecs.code_codec import CodeNode, render_compressed_code


def _clean_code_node(body: str, aggressive: bool = False) -> str:
    """Lightweight whitespace & redundant comment cleaner."""
    if not body:
        return ""
    lines = body.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Keep shebang or special directives, skip standalone comments if aggressive
        if aggressive and stripped.startswith("#") and not stripped.startswith("# ["):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def _format_log_node(node: Any, collapsed: bool = False) -> str:
    template = getattr(node, "template", "")
    count = getattr(node, "count", 1)
    samples = getattr(node, "sample_lines", [])

    if collapsed:
        return getattr(node, "stub", f"LOG TEMPLATE: {template} (occurred {count}x)")

    if count <= 2:
        return "\n".join(samples)

    sample_text = "\n".join(f"  > {s}" for s in samples)
    return f"LOG TEMPLATE: {template} (occurred {count}x)\nSamples:\n{sample_text}"


def prune_tokens(
    selected_nodes: list[Any],
    unchanged_pointers: list[Any],
    collapsed_nodes: Optional[list[Any]] = None,
    all_nodes: Optional[list[Any]] = None,
    domain: str = "code"
) -> str:
    """
    Renders the final compressed prompt.
    For Python code, leverages AST skeleton reconstruction so indentation
    and module syntax are 100% valid.
    """
    collapsed_nodes = collapsed_nodes or []

    # If domain is code and we have code nodes, use AST skeleton reconstruction
    if domain == "code" and (selected_nodes or collapsed_nodes):
        nodes_pool = all_nodes if all_nodes else (selected_nodes + collapsed_nodes)
        code_nodes = [n for n in nodes_pool if isinstance(n, CodeNode)]
        if code_nodes:
            selected_ids = {n.id for n in selected_nodes}
            collapsed_ids = {n.id for n in collapsed_nodes}
            code_result = render_compressed_code(code_nodes, selected_ids, collapsed_ids)

            # Append unchanged pointers if any
            if unchanged_pointers:
                ptr_lines = ["\n# [Unchanged session context (cached pointers):]"]
                for ptr in unchanged_pointers:
                    ptr_lines.append(f"# - {ptr.name}")
                code_result += "\n" + "\n".join(ptr_lines)

            return code_result

    # Non-code or fallback text/log rendering
    blocks = []
    for n in selected_nodes:
        kind = getattr(n, "kind", "text")
        if kind == "log_template":
            blocks.append(_format_log_node(n, collapsed=False))
        else:
            blocks.append(getattr(n, "body", str(n)))

    for n in collapsed_nodes:
        kind = getattr(n, "kind", "text")
        if kind == "log_template":
            blocks.append(_format_log_node(n, collapsed=True))
        else:
            blocks.append(getattr(n, "stub", str(n)))

    if unchanged_pointers:
        blocks.append("[Unchanged session context (cached pointers):]")
        for ptr in unchanged_pointers:
            blocks.append(f" - {ptr.name} (cached)")

    return "\n\n".join(b for b in blocks if b.strip())
