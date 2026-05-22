import ast
import base64
import io
import tokenize
import zlib


REV_MARKER = "# PT_REV:"


def strip_docstrings(node: ast.AST) -> ast.AST:  # buang docstring dari AST
    for child in ast.walk(node):
        if not isinstance(
            child, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        body = child.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            child.body = body[1:]
    return node


def token_minify(source: str) -> str:  # minify fallback pakai token Python
    tokens = []
    reader = io.StringIO(source).readline
    for token in tokenize.generate_tokens(reader):
        token_type, token_text, start, end, line = token
        if token_type == tokenize.COMMENT:
            continue
        tokens.append((token_type, token_text, start, end, line))
    result = tokenize.untokenize(tokens)
    return "\n".join(line.rstrip() for line in result.splitlines() if line.strip())


def minify_source(source: str) -> str:  # minify source utama pakai AST
    try:
        tree = ast.parse(source)
        tree = strip_docstrings(tree)
        ast.fix_missing_locations(tree)
        minified = ast.unparse(tree)
    except SyntaxError:
        minified = token_minify(source)
    return minified.strip() + "\n"


def make_loader(minified_source: str, reversible_payload: str | None) -> str:  # bikin filemob.py runnable
    compressed = zlib.compress(minified_source.encode("utf-8"), 9)
    packed = base64.b85encode(compressed).decode()[::-1]
    rev_line = f"{REV_MARKER}{reversible_payload}\n" if reversible_payload else ""
    return (
        rev_line
        + "import base64 as _b,zlib as _z\n"
        + f"_p={packed!r}[::-1]\n"
        + "getattr(__import__('builtins'),'exec')(_z.decompress(_b.b85decode(_p)))\n"
    )