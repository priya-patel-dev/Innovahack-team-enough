"""
Stage 2 (code): Structural Layer.

Parses source into a lightweight call/dependency graph instead of keeping
raw text. Each node = a function/class with its signature + docstring;
full body is attached but treated as "expandable on demand" so the query
router / budget allocator can decide whether it's worth the tokens.

Starter implementation targets Python via the `ast` module. Swap in
tree-sitter if you need multi-language support with the time you have.
"""
import ast
import hashlib
from dataclasses import dataclass, field


@dataclass
class CodeNode:
    id: str
    name: str
    kind: str  # "function" | "class" | "import"
    signature: str
    docstring: str
    body: str
    calls: list[str] = field(default_factory=list)
    token_estimate: int = 0

    def content_hash(self) -> str:
        return hashlib.sha256(self.body.encode()).hexdigest()


def build_code_graph(source: str) -> list[CodeNode]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Fall back: treat as opaque text chunk, don't crash the pipeline
        return [CodeNode(
            id="raw_0", name="raw_block", kind="text",
            signature="", docstring="", body=source,
            token_estimate=len(source.split()),
        )]

    nodes: list[CodeNode] = []

    for i, node in enumerate(ast.walk(tree)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            docstring = ast.get_docstring(node) or ""
            body = ast.unparse(node)
            calls = [
                n.func.id for n in ast.walk(node)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            ]
            signature = body.split("\n")[0]

            nodes.append(CodeNode(
                id=f"{node.__class__.__name__}_{i}_{node.name}",
                name=node.name,
                kind="function" if not isinstance(node, ast.ClassDef) else "class",
                signature=signature,
                docstring=docstring,
                body=body,
                calls=calls,
                token_estimate=len(body.split()),
            ))

    return nodes
