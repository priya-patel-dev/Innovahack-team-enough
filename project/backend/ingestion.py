"""
Stage 1: Ingestion Layer
Detects whether raw context is code, logs, or mixed, and routes to the
right codec. Keep this cheap and heuristic-based - not worth ML here.
"""
import re

LOG_LINE_PATTERN = re.compile(
    r"^\[?\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}"  # ISO-ish timestamp
    r"|^\d{2}/\d{2}/\d{4}"  # US date
    r"|(INFO|WARN|ERROR|DEBUG|TRACE)\b",
    re.MULTILINE,
)

CODE_HINTS = (
    "def ", "class ", "import ", "function ", "const ", "let ", "var ",
    "public ", "private ", "#include", "package ", "{", "};",
)


def detect_domain(context: str) -> str:
    """Return 'code', 'logs', or 'mixed'."""
    log_hits = len(LOG_LINE_PATTERN.findall(context))
    code_hits = sum(context.count(h) for h in CODE_HINTS)

    if log_hits > 5 and code_hits < log_hits / 4:
        return "logs"
    if code_hits > 5 and log_hits < code_hits / 4:
        return "code"
    return "mixed"
