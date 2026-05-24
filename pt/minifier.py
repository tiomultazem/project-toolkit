import ast
import base64
import builtins
import io
import keyword
import marshal
import os
import tokenize
import zlib


REV_MARKER = "# PT_REV:"

_RESERVED_NAMES = set(dir(builtins)) | set(keyword.kwlist) | {
    "__name__",
    "__file__",
    "__package__",
    "__loader__",
    "__spec__",
    "__doc__",
    "__annotations__",
    "__builtins__",
}


def _is_safe_rename(name: str) -> bool:  # cek nama boleh diacak
    return bool(name) and name not in _RESERVED_NAMES and not (
        name.startswith("__") and name.endswith("__")
    )


class _NameCollector(ast.NodeVisitor):  # kumpulkan nama yang bisa diacak
    def __init__(self) -> None:
        self.candidates: set[str] = set()
        self.protected: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.protected.add(alias.asname or alias.name.split(".")[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "*":
                continue
            self.protected.add(alias.asname or alias.name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._add(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._add(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._add(node.name)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        self._add(node.arg)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self._add(node.id)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self._add(node.name)
        self.generic_visit(node)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        if node.name:
            self._add(node.name)
        self.generic_visit(node)

    def visit_MatchStar(self, node: ast.MatchStar) -> None:
        if node.name:
            self._add(node.name)
        self.generic_visit(node)

    def _add(self, name: str) -> None:
        if _is_safe_rename(name):
            self.candidates.add(name)


class _NameObfuscator(ast.NodeTransformer):  # ubah nama jadi pendek dan acak rasa
    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.name = self.mapping.get(node.name, node.name)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        node.name = self.mapping.get(node.name, node.name)
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        node.name = self.mapping.get(node.name, node.name)
        self.generic_visit(node)
        return node

    def visit_arg(self, node: ast.arg) -> ast.AST:
        node.arg = self.mapping.get(node.arg, node.arg)
        return node

    def visit_Name(self, node: ast.Name) -> ast.AST:
        node.id = self.mapping.get(node.id, node.id)
        return node

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> ast.AST:
        if node.name:
            node.name = self.mapping.get(node.name, node.name)
        self.generic_visit(node)
        return node

    def visit_Global(self, node: ast.Global) -> ast.AST:
        node.names = [self.mapping.get(name, name) for name in node.names]
        return node

    def visit_Nonlocal(self, node: ast.Nonlocal) -> ast.AST:
        node.names = [self.mapping.get(name, name) for name in node.names]
        return node

    def visit_MatchAs(self, node: ast.MatchAs) -> ast.AST:
        if node.name:
            node.name = self.mapping.get(node.name, node.name)
        self.generic_visit(node)
        return node

    def visit_MatchStar(self, node: ast.MatchStar) -> ast.AST:
        if node.name:
            node.name = self.mapping.get(node.name, node.name)
        self.generic_visit(node)
        return node


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


def _make_mapping(tree: ast.AST) -> dict[str, str]:  # bikin peta rename identifier
    collector = _NameCollector()
    collector.visit(tree)
    names = sorted(collector.candidates - collector.protected)
    return {name: f"_p{index:x}" for index, name in enumerate(names)}


def obfuscate_names(tree: ast.AST) -> ast.AST:  # acak nama variable/function/class
    mapping = _make_mapping(tree)
    if not mapping:
        return tree
    return _NameObfuscator(mapping).visit(tree)


def _unique_decoder_name(tree: ast.AST) -> str:  # bikin nama decoder yang tidak tabrakan
    used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    used.update(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    )
    base = "_pt_s"
    if base not in used:
        return base
    index = 0
    while f"{base}{index}" in used:
        index += 1
    return f"{base}{index}"


def _encode_string(value: str, key: int) -> tuple[int, ...]:  # ubah string jadi angka acak
    return tuple(
        (ord(char) + (key % 11)) ^ ((key + index * 17) % 251)
        for index, char in enumerate(value)
    )


class _StringObfuscator(ast.NodeTransformer):  # ubah string literal jadi decoder call
    def __init__(self, decoder_name: str) -> None:
        self.decoder_name = decoder_name

    def visit_JoinedStr(self, node: ast.JoinedStr) -> ast.AST:
        return node

    def visit_MatchValue(self, node: ast.MatchValue) -> ast.AST:
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if not isinstance(node.value, str):
            return node
        key = (sum(ord(char) for char in node.value) + len(node.value) * 31) % 251
        if key == 0:
            key = 97
        encoded = _encode_string(node.value, key)
        return ast.copy_location(
            ast.Call(
                func=ast.Name(id=self.decoder_name, ctx=ast.Load()),
                args=[
                    ast.Tuple(
                        elts=[ast.Constant(value=item) for item in encoded],
                        ctx=ast.Load(),
                    ),
                    ast.Constant(value=key),
                ],
                keywords=[],
            ),
            node,
        )


def _decoder_function(decoder_name: str) -> ast.FunctionDef:  # fungsi runtime pembuka string
    source = f"""
def {decoder_name}(_d, _k):
    def _c(_i, _v):
        return chr(((_v ^ ((_k + _i * 17) % 251)) - (_k % 11)) % 1114111)
    return chr(0)[:0].join(_c(_i, _v) for _i, _v in enumerate(_d))
"""
    return ast.parse(source).body[0]


def _future_import_index(tree: ast.Module) -> int:  # cari batas import __future__
    index = 0
    for node in tree.body:
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "__future__"
        ):
            index += 1
            continue
        break
    return index


def obfuscate_strings(tree: ast.AST) -> ast.AST:  # sembunyikan string literal
    if not isinstance(tree, ast.Module):
        return tree
    decoder_name = _unique_decoder_name(tree)
    tree = _StringObfuscator(decoder_name).visit(tree)
    decoder = _decoder_function(decoder_name)
    tree.body.insert(_future_import_index(tree), decoder)
    return tree


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


def minify_source(source: str) -> str:  # hard minify + rename identifier
    try:
        tree = ast.parse(source)
        tree = strip_docstrings(tree)
        tree = obfuscate_names(tree)
        tree = obfuscate_strings(tree)
        ast.fix_missing_locations(tree)
        minified = ast.unparse(tree)
    except SyntaxError:
        minified = token_minify(source)
    return minified.strip() + "\n"


def _chunks(text: str, size: int = 73) -> list[str]:  # pecah payload jadi chunk kecil
    return [text[index : index + size] for index in range(0, len(text), size)]


def _masked_code_bytes(minified_source: str) -> tuple[str, list[int]]:  # compile, compress, xor, encode
    code = compile(minified_source, "<pt-mini>", "exec")
    packed = zlib.compress(marshal.dumps(code), 9)
    key = list(os.urandom(17))
    masked = bytes(byte ^ key[index % len(key)] for index, byte in enumerate(packed))
    return base64.b85encode(masked).decode()[::-1], key


def make_loader(minified_source: str, reversible_payload: str | None) -> str:  # bikin filemob.py runnable
    packed, key = _masked_code_bytes(minified_source)
    parts = _chunks(packed)
    table = [(index * 7 + 3, part) for index, part in enumerate(parts)]
    rev_line = f"{REV_MARKER}{reversible_payload}\n" if reversible_payload else ""
    return (
        rev_line
        + "import sys as _0\n"
        + "if getattr(_0,'gettrace')():raise SystemExit\n"
        + "_1=__import__;_2=_1('builtins');_3=_1('base64');_4=_1('zlib');_5=_1('marshal')\n"
        + f"_6={table!r}\n"
        + "_7=''.join(_9 for _8,_9 in sorted(_6,key=lambda _a:_a[0]))[::-1]\n"
        + f"_k={key!r}\n"
        + "_d=bytearray(_3.b85decode(_7))\n"
        + "for _i in range(len(_d)):_d[_i]^=_k[_i%len(_k)]\n"
        + "getattr(_2,'exec')(_5.loads(_4.decompress(bytes(_d))))\n"
    )