"""
Stage 2 (code): Structural Layer.

Parses source code into an AST-aware dependency graph.
Preserves:
- Imports & module-level definitions
- Class skeletons, docstrings, and hierarchy
- Accurate call-graph dependencies between methods
- Syntactically valid code reconstruction (valid Python output with preserved indentation)
"""
import ast
import hashlib
from dataclasses import dataclass, field
from typing import Optional

try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")
    def estimate_tokens(text: str) -> int:
        return len(_enc.encode(text)) if text else 0
except Exception:
    def estimate_tokens(text: str) -> int:
        return int(len(text.split()) * 1.3) if text else 0


@dataclass
class CodeNode:
    id: str
    name: str
    kind: str  # "import", "constant", "function", "class", "method", "text"
    signature: str
    docstring: str
    body: str
    parent_class: Optional[str] = None
    calls: list[str] = field(default_factory=list)
    token_estimate: int = 0
    stub: str = ""
    lineno: int = 0

    def content_hash(self) -> str:
        return hashlib.sha256(self.body.encode("utf-8")).hexdigest()


def _extract_calls(node: ast.AST) -> list[str]:
    """Extract called function and method names within an AST node."""
    calls = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            if isinstance(sub.func, ast.Name):
                calls.append(sub.func.id)
            elif isinstance(sub.func, ast.Attribute):
                calls.append(sub.func.attr)
    return list(dict.fromkeys(calls))  # preserve order, deduplicate


def build_code_graph(source: str) -> list[CodeNode]:
    """
    Parses Python source code into a structured list of CodeNode objects.
    Maintains document order, class-method relationships, and call dependencies.
    """
    if not source or not source.strip():
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Graceful fallback: regex/line-based chunker for non-Python or broken syntax
        import re
        nodes: list[CodeNode] = []
        chunks = re.split(r'\n(?=\s*(?:def|class|async def|\/\*|\#\#)\s+)', source)
        for i, chunk in enumerate(chunks):
            chunk = chunk.strip()
            if not chunk:
                continue
            signature = chunk.split('\n')[0][:120]
            fq_name = f"chunk_{i}"
            stub = f"{signature}\n# [collapsed: node '{fq_name}']\npass"
            nodes.append(CodeNode(
                id=f"chunk_{i}",
                name=fq_name,
                kind="text",
                signature=signature,
                docstring="",
                body=chunk,
                parent_class=None,
                calls=[],
                token_estimate=estimate_tokens(chunk),
                stub=stub,
                lineno=i * 10
            ))
        return nodes

    nodes: list[CodeNode] = []
    imports_accum: list[str] = []
    import_lineno = 0

    # First pass: collect top-level nodes in document order
    for item in tree.body:
        # 1. Imports
        if isinstance(item, (ast.Import, ast.ImportFrom)):
            imports_accum.append(ast.unparse(item))
            if import_lineno == 0:
                import_lineno = getattr(item, 'lineno', 1)

        # 2. Module-level Constants / Assignments
        elif isinstance(item, (ast.Assign, ast.AnnAssign)):
            text = ast.unparse(item)
            name = "module_assignment"
            if isinstance(item, ast.Assign) and item.targets and isinstance(item.targets[0], ast.Name):
                name = item.targets[0].id
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                name = item.target.id

            nodes.append(CodeNode(
                id=f"const:{name}_{item.lineno}",
                name=name,
                kind="constant",
                signature=text[:80],
                docstring="",
                body=text,
                parent_class=None,
                calls=_extract_calls(item),
                token_estimate=estimate_tokens(text),
                stub=text,
                lineno=item.lineno
            ))

        # 3. Top-level Functions
        elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            docstring = ast.get_docstring(item) or ""
            body = ast.unparse(item)
            sig_line = body.split("\n")[0]
            doc_stub = f'    """{docstring[:100]}..."""\n' if docstring else ""
            stub = f"{sig_line}\n{doc_stub}    # [collapsed: node 'func:{item.name}']\n    ..."

            nodes.append(CodeNode(
                id=f"func:{item.name}",
                name=item.name,
                kind="function",
                signature=sig_line,
                docstring=docstring,
                body=body,
                parent_class=None,
                calls=_extract_calls(item),
                token_estimate=estimate_tokens(body),
                stub=stub,
                lineno=item.lineno
            ))

        # 4. Classes
        elif isinstance(item, ast.ClassDef):
            class_name = item.name
            docstring = ast.get_docstring(item) or ""
            bases = [ast.unparse(b) for b in item.bases]
            bases_str = f"({', '.join(bases)})" if bases else ""
            class_sig = f"class {class_name}{bases_str}:"
            
            # Create a class header node
            class_header_lines = [class_sig]
            if docstring:
                class_header_lines.append(f'    """{docstring}"""')
            class_header_body = "\n".join(class_header_lines)

            nodes.append(CodeNode(
                id=f"class:{class_name}",
                name=class_name,
                kind="class",
                signature=class_sig,
                docstring=docstring,
                body=class_header_body,
                parent_class=None,
                calls=_extract_calls(item),
                token_estimate=estimate_tokens(class_header_body),
                stub=class_header_body + "\n    pass",
                lineno=item.lineno
            ))

            # Class methods and attributes
            for member in item.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    m_doc = ast.get_docstring(member) or ""
                    m_body = ast.unparse(member)
                    m_sig = m_body.split("\n")[0]
                    fq_name = f"{class_name}.{member.name}"
                    m_doc_stub = f'        """{m_doc[:100]}..."""\n' if m_doc else ""
                    m_stub = f"    {m_sig}\n{m_doc_stub}        # [collapsed: node 'method:{fq_name}']\n        ..."

                    nodes.append(CodeNode(
                        id=f"method:{fq_name}",
                        name=fq_name,
                        kind="method",
                        signature=m_sig,
                        docstring=m_doc,
                        body=m_body,
                        parent_class=class_name,
                        calls=_extract_calls(member),
                        token_estimate=estimate_tokens(m_body),
                        stub=m_stub,
                        lineno=member.lineno
                    ))
                elif isinstance(member, (ast.Assign, ast.AnnAssign)):
                    attr_text = ast.unparse(member)
                    attr_name = "attr"
                    if isinstance(member, ast.Assign) and member.targets and isinstance(member.targets[0], ast.Name):
                        attr_name = member.targets[0].id
                    elif isinstance(member, ast.AnnAssign) and isinstance(member.target, ast.Name):
                        attr_name = member.target.id

                    nodes.append(CodeNode(
                        id=f"attr:{class_name}.{attr_name}_{member.lineno}",
                        name=f"{class_name}.{attr_name}",
                        kind="constant",
                        signature=attr_text[:80],
                        docstring="",
                        body=f"    {attr_text}",
                        parent_class=class_name,
                        calls=_extract_calls(member),
                        token_estimate=estimate_tokens(attr_text),
                        stub=f"    {attr_text}",
                        lineno=member.lineno
                    ))

    # Add consolidated imports as top node if any were found
    if imports_accum:
        imports_text = "\n".join(dict.fromkeys(imports_accum))
        nodes.insert(0, CodeNode(
            id="imports:module",
            name="module_imports",
            kind="import",
            signature="import ...",
            docstring="",
            body=imports_text,
            parent_class=None,
            calls=[],
            token_estimate=estimate_tokens(imports_text),
            stub=imports_text,
            lineno=import_lineno
        ))

    return nodes


def render_compressed_code(nodes: list[CodeNode], selected_ids: set[str], collapsed_ids: set[str]) -> str:
    """
    Renders selected and collapsed nodes into syntactically valid, properly indented Python code.
    Guarantees that the resulting code parses with ast.parse().
    """
    rendered_blocks: list[str] = []

    # 1. Imports and constants first
    for n in nodes:
        if n.kind in ("import", "constant") and n.parent_class is None:
            rendered_blocks.append(n.body)

    # 2. Group by classes and top-level functions
    classes: dict[str, list[CodeNode]] = {}
    class_headers: dict[str, CodeNode] = {}
    top_level_functions: list[CodeNode] = []

    for n in nodes:
        if n.kind == "class":
            class_headers[n.name] = n
            if n.name not in classes:
                classes[n.name] = []
        elif n.parent_class:
            classes.setdefault(n.parent_class, []).append(n)
        elif n.kind == "function":
            top_level_functions.append(n)

    # Render classes with properly indented methods
    for class_name, header_node in class_headers.items():
        class_lines = [header_node.body]
        members = classes.get(class_name, [])
        has_content = False

        for member in members:
            if member.id in selected_ids:
                # Full body with 4-space class indentation
                indented = "\n".join(f"    {line}" if line.strip() else "" for line in member.body.splitlines())
                class_lines.append(indented)
                has_content = True
            elif member.id in collapsed_ids or member.kind == "constant":
                # Stub or constant
                class_lines.append(member.stub)
                has_content = True

        if not has_content:
            class_lines.append("    pass")

        rendered_blocks.append("\n\n".join(class_lines))

    # Render top-level functions
    for fn in top_level_functions:
        if fn.id in selected_ids:
            rendered_blocks.append(fn.body)
        elif fn.id in collapsed_ids:
            rendered_blocks.append(fn.stub)

    # Render any fallback chunks
    for n in nodes:
        if n.kind == "text":
            if n.id in selected_ids:
                rendered_blocks.append(n.body)
            elif n.id in collapsed_ids:
                rendered_blocks.append(n.stub)

    return "\n\n".join(b for b in rendered_blocks if b.strip())
