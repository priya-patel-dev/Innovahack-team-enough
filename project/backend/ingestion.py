"""
Stage 1: Ingestion Layer.

Detects whether raw context is code, logs, or mixed, and routes to the right codec.
Uses AST validation + syntax heuristics for code, and timestamp/log-level detection for logs.
"""
import ast
import re

LOG_LINE_PATTERN = re.compile(
    r"^\[?\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}"  # ISO timestamp
    r"|^\d{2}/\d{2}/\d{4}"                         # US date
    r"|(INFO|WARN|ERROR|DEBUG|TRACE|FATAL)\b",
    re.MULTILINE
)

CODE_HINTS = (
    "def ", "class ", "import ", "from ", "function ", "const ", "let ", "var ",
    "public ", "private ", "#include", "package ", "{", "};", "return "
)


def detect_domain(context: str) -> str:
    """
    Returns 'code', 'logs', or 'mixed'.
    """
    if not context or not context.strip():
        return "mixed"

    # Quick test: if Python AST parses without syntax errors, it is Python code
    try:
        ast.parse(context)
        # Verify it's not just a single plain word
        if any(hint in context for hint in ("def ", "class ", "import ", "from ", "return ", "=")):
            return "code"
    except SyntaxError:
        pass

    log_hits = len(LOG_LINE_PATTERN.findall(context))
    code_hits = sum(context.count(h) for h in CODE_HINTS)

    if log_hits > 0 and code_hits == 0:
        return "logs"
    if code_hits > 0 and log_hits == 0:
        return "code"
    if log_hits > 3 and code_hits < log_hits / 3:
        return "logs"
    if code_hits > 3 and log_hits < code_hits / 3:
        return "code"

    return "mixed"
