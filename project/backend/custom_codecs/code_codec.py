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
    stub: str = ""

    def content_hash(self) -> str:
        return hashlib.sha256(self.body.encode()).hexdigest()


class ASTTypeStripper(ast.NodeTransformer):
    """AST visitor that recursively strips Python type annotations."""
    def visit_FunctionDef(self, node):
        node.returns = None
        for arg in node.args.args:
            arg.annotation = None
        for arg in node.args.kwonlyargs:
            arg.annotation = None
        if node.args.vararg:
            node.args.vararg.annotation = None
        if node.args.kwarg:
            node.args.kwarg.annotation = None
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        node.returns = None
        for arg in node.args.args:
            arg.annotation = None
        for arg in node.args.kwonlyargs:
            arg.annotation = None
        if node.args.vararg:
            node.args.vararg.annotation = None
        if node.args.kwarg:
            node.args.kwarg.annotation = None
        self.generic_visit(node)
        return node

    def visit_AnnAssign(self, node):
        if node.value:
            return ast.Assign(targets=[node.target], value=node.value)
        return None

    def visit_arg(self, node):
        node.annotation = None
        return node


def build_code_graph(source: str) -> list[CodeNode]:
    try:
        tree = ast.parse(source)
        # Strip types!
        tree = ASTTypeStripper().visit(tree)
        ast.fix_missing_locations(tree)
    except SyntaxError:
        # Fall back: regex/line-based chunker for messy code
        import re
        nodes: list[CodeNode] = []
        # Split by typical block starters (def, class, etc) or blank lines
        chunks = re.split(r'\n(?=\s*(?:def|class|async def|\/\*|\#\#)\s+)', source)
        for i, chunk in enumerate(chunks):
            chunk = chunk.strip()
            if not chunk: continue
            signature = chunk.split('\n')[0][:100]
            fq_name = f"chunk_{i}"
            nodes.append(CodeNode(
                id=f"regex_chunk_{i}",
                name=fq_name,
                kind="text",
                signature=signature,
                docstring="",
                body=chunk,
                token_estimate=len(chunk.split()),
                stub=f"{signature}\n# [collapsed: query Stage 7 with '{fq_name}' to recover]\npass"
            ))
        return nodes

    nodes: list[CodeNode] = []

    # Build parent mapping to identify class methods
    parent_map = {}
    for p in ast.walk(tree):
        for child in ast.iter_child_nodes(p):
            parent_map[child] = p

    for i, node in enumerate(ast.walk(tree)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            docstring = ast.get_docstring(node) or ""
            body = ast.unparse(node)
            calls = [
                n.func.id for n in ast.walk(node)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            ]
            
            parent = parent_map.get(node)
            prefix = ""
            if parent and isinstance(parent, ast.ClassDef):
                prefix = f"{parent.name}."
                
            signature = body.split("\n")[0]
            fq_name = f"{prefix}{node.name}"
            stub = f"{signature}\n    # [collapsed: query Stage 7 with '{fq_name}' to recover]\n    pass"

            nodes.append(CodeNode(
                id=f"{node.__class__.__name__}_{i}_{fq_name}",
                name=fq_name,
                kind="function",
                signature=signature,
                docstring=docstring,
                body=body,
                calls=calls,
                token_estimate=len(body.split()),
                stub=stub
            ))
        elif isinstance(node, ast.ClassDef):
            docstring = ast.get_docstring(node) or ""
            class_body = f"class {node.name}:\n"
            if docstring:
                class_body += f'    """{docstring}"""\n'
            class_body += "    pass"
            
            nodes.append(CodeNode(
                id=f"ClassDef_{i}_{node.name}",
                name=node.name,
                kind="class",
                signature=f"class {node.name}:",
                docstring=docstring,
                body=class_body,
                calls=[],
                token_estimate=len(class_body.split()),
                stub=class_body
            ))

    return nodes
