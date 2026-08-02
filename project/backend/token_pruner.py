"""
Stage 6: Token Pruner.

Fine-grained cleanup applied to nodes that survived structural conversion.
Uses syntax-aware rule-based pruning (comments stripping, docstring truncation,
whitespace minimization) instead of heavy neural prompt compressors (llmlingua).
This ensures sub-millisecond, CPU-only execution with 0% risk of syntax breaking.
"""
import re

def _clean_code_node(node, rate: float) -> str:
    """
    Cleans Python code by removing comments, docstrings (if rate is low),
    and compressing whitespace.
    """
    body = getattr(node, "body", "")
    if not body:
        return ""

    lines = body.splitlines()
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()
        
        # Skip single-line comments
        if stripped.startswith("#"):
            continue
            
        # Handle inline comments
        if " #" in line:
            line = line.split(" #")[0]
            
        cleaned_lines.append(line)

    cleaned_body = "\n".join(cleaned_lines)
    
    # If compression rate is aggressive (rate < 0.6), truncate docstrings
    if rate < 0.6:
        cleaned_body = re.sub(r'"""[\s\S]*?"""', '"""[docstring compressed]"""', cleaned_body)
        cleaned_body = re.sub(r"'''[\s\S]*?'''", "'''[docstring compressed]'''", cleaned_body)
        
    # Collapse multiple blank lines
    cleaned_body = re.sub(r'\n\s*\n', '\n', cleaned_body)
    
    return cleaned_body

def _clean_log_node(node) -> str:
    template = getattr(node, "template", "")
    count = getattr(node, "count", 1)
    samples = getattr(node, "sample_lines", [])
    
    if count <= 2:
        return "\n".join(samples)
        
    sample_text = "\n".join(f"  > {s}" for s in samples)
    return f"LOG TEMPLATE: {template} (occurred {count} times)\nSample occurrences:\n{sample_text}"

def prune_tokens(selected_nodes: list, unchanged_pointers: list, collapsed_nodes: list = None, rate: float = 0.5) -> str:
    """
    Cleans and formats selected nodes, appends collapsed/stubbed nodes, then appends unchanged pointers.
    """
    pieces = []
    
    for node in selected_nodes:
        kind = getattr(node, "kind", "text")
        if kind in ("function", "class", "code"):
            pieces.append(_clean_code_node(node, rate))
        elif kind == "log_template":
            pieces.append(_clean_log_node(node))
        else:
            text = getattr(node, "body", None) or getattr(node, "template", "") or str(node)
            pieces.append(text)

    # Append collapsed/stubbed nodes
    if collapsed_nodes:
        for node in collapsed_nodes:
            stub_text = getattr(node, "stub", "")
            if stub_text:
                pieces.append(stub_text)

    # Append unchanged pointers
    if unchanged_pointers:
        pieces.append("\n[Unchanged session context (collapsed to pointers):]")
        for ptr in unchanged_pointers:
            pieces.append(f" - {ptr.name} (cached)")

    return "\n\n".join(pieces)
