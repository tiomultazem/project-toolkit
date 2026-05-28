import ast
import base64
import builtins
import copy
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


def _argument_names(args: ast.arguments) -> set[str]:  # nama argumen harus stabil untuk keyword call/framework
    result = set()
    for arg in (
        list(args.posonlyargs)
        + list(args.args)
        + list(args.kwonlyargs)
    ):
        result.add(arg.arg)
    if args.vararg:
        result.add(args.vararg.arg)
    if args.kwarg:
        result.add(args.kwarg.arg)
    return result


def _import_alias_name(alias: ast.alias) -> str:  # nama binding dari import
    return alias.asname or alias.name.split(".")[0]


class _UsedNameCollector(ast.NodeVisitor):  # kumpulkan semua nama supaya hasil rename tidak tabrakan
    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        self.names.add(node.id)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.names.add(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.names.add(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.names.add(node.name)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        self.names.add(node.arg)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self.names.add(node.name)
        self.generic_visit(node)

    def visit_Global(self, node: ast.Global) -> None:
        self.names.update(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self.names.update(node.names)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        if node.name:
            self.names.add(node.name)
        self.generic_visit(node)

    def visit_MatchStar(self, node: ast.MatchStar) -> None:
        if node.name:
            self.names.add(node.name)
        self.generic_visit(node)


class _NameGenerator:  # pembuat nama obfuscated yang unik
    def __init__(self, tree: ast.AST) -> None:
        collector = _UsedNameCollector()
        collector.visit(tree)
        self.used = set(collector.names) | _RESERVED_NAMES
        self.index = 0

    def next(self) -> str:
        while True:
            name = f"_ptv{self.index:x}"
            self.index += 1
            if name not in self.used:
                self.used.add(name)
                return name


class _YieldDetector(ast.NodeVisitor):  # cek fungsi generator tanpa tertipu nested scope
    def __init__(self) -> None:
        self.has_yield = False

    def visit_Yield(self, node: ast.Yield) -> None:
        self.has_yield = True

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        self.has_yield = True

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return


def _function_has_yield(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    detector = _YieldDetector()
    for item in node.body:
        detector.visit(item)
        if detector.has_yield:
            break
    return detector.has_yield


def _decorator_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return None


def _first_positional_arg(args: ast.arguments) -> str | None:
    positional_args = list(args.posonlyargs) + list(args.args)
    if not positional_args:
        return None
    return positional_args[0].arg


def _clone_arguments(args: ast.arguments) -> ast.arguments:
    return copy.deepcopy(args)


def _forward_call_args(
    args: ast.arguments, skip_first_positional: bool = False
) -> tuple[list[ast.expr], list[ast.keyword]]:
    positional_args = list(args.posonlyargs) + list(args.args)
    if skip_first_positional and positional_args:
        positional_args = positional_args[1:]

    call_args: list[ast.expr] = [
        ast.Name(id=arg.arg, ctx=ast.Load()) for arg in positional_args
    ]
    if args.vararg:
        call_args.append(
            ast.Starred(
                value=ast.Name(id=args.vararg.arg, ctx=ast.Load()),
                ctx=ast.Load(),
            )
        )

    keywords = [
        ast.keyword(arg=arg.arg, value=ast.Name(id=arg.arg, ctx=ast.Load()))
        for arg in args.kwonlyargs
    ]
    if args.kwarg:
        keywords.append(
            ast.keyword(
                arg=None,
                value=ast.Name(id=args.kwarg.arg, ctx=ast.Load()),
            )
        )
    return call_args, keywords


class _FunctionFacadeObfuscator(ast.NodeTransformer):  # body asli pindah ke fungsi internal acak
    def __init__(self, generator: _NameGenerator) -> None:
        self.generator = generator

    def visit_Module(self, node: ast.Module) -> ast.AST:
        node.body = self._split_body(node.body, in_class=False)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        node.decorator_list = [self.visit(item) for item in node.decorator_list]
        node.bases = [self.visit(item) for item in node.bases]
        node.keywords = [self.visit(item) for item in node.keywords]
        node.body = self._split_body(node.body, in_class=True)
        return node

    def _split_body(self, body: list[ast.stmt], in_class: bool) -> list[ast.stmt]:
        result: list[ast.stmt] = []
        for item in body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                internal_name = self.generator.next()
                internal_function = self._internal_function(item, internal_name)
                facade_function = self._facade_function(item, internal_name, in_class)
                result.extend([internal_function, facade_function])
                continue
            result.append(self.visit(item))
        return result

    def _internal_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, internal_name: str
    ) -> ast.FunctionDef | ast.AsyncFunctionDef:
        internal_function = copy.deepcopy(node)
        internal_function.name = internal_name
        internal_function.decorator_list = []
        return internal_function

    def _facade_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        internal_name: str,
        in_class: bool,
    ) -> ast.FunctionDef | ast.AsyncFunctionDef:
        facade_function = copy.deepcopy(node)
        facade_function.args = _clone_arguments(node.args)
        facade_function.body = [
            self._facade_body_statement(node, internal_name, in_class)
        ]
        return facade_function

    def _facade_body_statement(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        internal_name: str,
        in_class: bool,
    ) -> ast.stmt:
        call = self._internal_call(node, internal_name, in_class)
        has_yield = _function_has_yield(node)
        if isinstance(node, ast.AsyncFunctionDef):
            if has_yield:
                item_name = self.generator.next()
                return ast.AsyncFor(
                    target=ast.Name(id=item_name, ctx=ast.Store()),
                    iter=call,
                    body=[
                        ast.Expr(
                            value=ast.Yield(
                                value=ast.Name(id=item_name, ctx=ast.Load())
                            )
                        )
                    ],
                    orelse=[],
                )
            return ast.Return(value=ast.Await(value=call))
        if has_yield:
            return ast.Return(value=ast.YieldFrom(value=call))
        return ast.Return(value=call)

    def _internal_call(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        internal_name: str,
        in_class: bool,
    ) -> ast.Call:
        skip_first = False
        if in_class:
            binding_kind = self._binding_kind(node.decorator_list)
            first_arg = _first_positional_arg(node.args)
            if binding_kind == "normal" and first_arg:
                target: ast.expr = ast.Attribute(
                    value=ast.Name(id=first_arg, ctx=ast.Load()),
                    attr=internal_name,
                    ctx=ast.Load(),
                )
                skip_first = True
            elif binding_kind == "classmethod" and first_arg:
                target = ast.Attribute(
                    value=ast.Name(id=first_arg, ctx=ast.Load()),
                    attr=internal_name,
                    ctx=ast.Load(),
                )
            else:
                target = ast.Attribute(
                    value=ast.Name(id="__class__", ctx=ast.Load()),
                    attr=internal_name,
                    ctx=ast.Load(),
                )
        else:
            target = ast.Name(id=internal_name, ctx=ast.Load())

        call_args, keywords = _forward_call_args(node.args, skip_first)
        return ast.Call(func=target, args=call_args, keywords=keywords)

    def _binding_kind(self, decorators: list[ast.expr]) -> str:
        names = {_decorator_name(decorator) for decorator in decorators}
        if "staticmethod" in names:
            return "staticmethod"
        if "classmethod" in names:
            return "classmethod"
        return "normal"


_DYNAMIC_LOCAL_CALLS = {"eval", "exec", "locals", "vars"}


class _DynamicLookupDetector(ast.NodeVisitor):  # deteksi akses nama lokal via string/dict
    def __init__(self) -> None:
        self.found = False

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in _DYNAMIC_LOCAL_CALLS:
            self.found = True
            return
        self.generic_visit(node)


def _has_dynamic_lookup(nodes: list[ast.stmt] | ast.AST) -> bool:
    detector = _DynamicLookupDetector()
    if isinstance(nodes, list):
        for node in nodes:
            detector.visit(node)
            if detector.found:
                break
    else:
        detector.visit(nodes)
    return detector.found


class _NonlocalNameCollector(ast.NodeVisitor):  # nama nonlocal harus tetap sama di semua scope terkait
    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self.names.update(node.names)


def _nonlocal_names(nodes: list[ast.stmt] | ast.AST) -> set[str]:
    collector = _NonlocalNameCollector()
    if isinstance(nodes, list):
        for node in nodes:
            collector.visit(node)
    else:
        collector.visit(nodes)
    return collector.names


class _LocalBindingCollector(ast.NodeVisitor):  # kumpulkan binding lokal tanpa masuk scope anak
    def __init__(self) -> None:
        self.bindings: set[str] = set()
        self.protected: set[str] = set()
        self.global_names: set[str] = set()
        self.nonlocal_names: set[str] = set()
        self.has_dynamic_local_lookup = False

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.protected.add(_import_alias_name(alias))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name != "*":
                self.protected.add(alias.asname or alias.name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.protected.add(node.name)
        for decorator in node.decorator_list:
            self.visit(decorator)
        self._visit_arguments_runtime_parts(node.args)
        if node.returns:
            self.visit(node.returns)
        self.protected.update(_nonlocal_names(node.body))
        if _has_dynamic_lookup(node.body):
            self.has_dynamic_local_lookup = True

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.protected.add(node.name)
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword_node in node.keywords:
            self.visit(keyword_node)
        if _has_dynamic_lookup(node.body):
            self.has_dynamic_local_lookup = True

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._visit_arguments_runtime_parts(node.args)
        if _has_dynamic_lookup(node.body):
            self.has_dynamic_local_lookup = True

    def visit_Global(self, node: ast.Global) -> None:
        self.global_names.update(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self.nonlocal_names.update(node.names)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.bindings.add(node.id)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self.bindings.add(node.name)
        self.generic_visit(node)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        if node.name:
            self.bindings.add(node.name)
        self.generic_visit(node)

    def visit_MatchStar(self, node: ast.MatchStar) -> None:
        if node.name:
            self.bindings.add(node.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in _DYNAMIC_LOCAL_CALLS:
            self.has_dynamic_local_lookup = True
        self.generic_visit(node)

    def _visit_arguments_runtime_parts(self, args: ast.arguments) -> None:
        for arg in (
            list(args.posonlyargs)
            + list(args.args)
            + list(args.kwonlyargs)
        ):
            if arg.annotation:
                self.visit(arg.annotation)
        if args.vararg and args.vararg.annotation:
            self.visit(args.vararg.annotation)
        if args.kwarg and args.kwarg.annotation:
            self.visit(args.kwarg.annotation)
        for default in list(args.defaults) + [item for item in args.kw_defaults if item]:
            self.visit(default)


class _ClassBindingCollector(ast.NodeVisitor):  # nama class attribute/method jangan ikut rename
    def __init__(self) -> None:
        self.protected: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.protected.add(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.protected.add(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.protected.add(node.name)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.protected.add(_import_alias_name(alias))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name != "*":
                self.protected.add(alias.asname or alias.name)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.protected.add(node.id)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self.protected.add(node.name)
        self.generic_visit(node)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        if node.name:
            self.protected.add(node.name)
        self.generic_visit(node)

    def visit_MatchStar(self, node: ast.MatchStar) -> None:
        if node.name:
            self.protected.add(node.name)
        self.generic_visit(node)


class _ScopeFrame:
    def __init__(self, mapping: dict[str, str], protected: set[str]) -> None:
        self.mapping = mapping
        self.protected = protected


class _ScopedNameObfuscator(ast.NodeTransformer):  # rename hanya variabel lokal yang aman
    def __init__(self, generator: _NameGenerator) -> None:
        self.generator = generator
        self.frames: list[_ScopeFrame] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self._visit_function_runtime_parts(node)
        frame = self._make_function_frame(node)
        self.frames.append(frame)
        node.body = [self.visit(item) for item in node.body]
        self.frames.pop()
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        return self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        node.decorator_list = [self.visit(item) for item in node.decorator_list]
        node.bases = [self.visit(item) for item in node.bases]
        node.keywords = [self.visit(item) for item in node.keywords]
        collector = _ClassBindingCollector()
        for item in node.body:
            collector.visit(item)
        self.frames.append(_ScopeFrame({}, collector.protected))
        node.body = [self.visit(item) for item in node.body]
        self.frames.pop()
        return node

    def visit_Lambda(self, node: ast.Lambda) -> ast.AST:
        self._visit_arguments_runtime_parts(node.args)
        protected = _argument_names(node.args) | self._lambda_binding_names(node)
        self.frames.append(_ScopeFrame({}, protected))
        node.body = self.visit(node.body)
        self.frames.pop()
        return node

    def visit_Name(self, node: ast.Name) -> ast.AST:
        node.id = self._mapped_name(node.id)
        return node

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> ast.AST:
        if node.name:
            node.name = self._mapped_name(node.name)
        self.generic_visit(node)
        return node

    def visit_Global(self, node: ast.Global) -> ast.AST:
        return node

    def visit_Nonlocal(self, node: ast.Nonlocal) -> ast.AST:
        return node

    def visit_MatchAs(self, node: ast.MatchAs) -> ast.AST:
        if node.name:
            node.name = self._mapped_name(node.name)
        self.generic_visit(node)
        return node

    def visit_MatchStar(self, node: ast.MatchStar) -> ast.AST:
        if node.name:
            node.name = self._mapped_name(node.name)
        self.generic_visit(node)
        return node

    def _mapped_name(self, name: str) -> str:
        for frame in reversed(self.frames):
            if name in frame.mapping:
                return frame.mapping[name]
            if name in frame.protected:
                return name
        return name

    def _make_function_frame(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> _ScopeFrame:
        collector = _LocalBindingCollector()
        for item in node.body:
            collector.visit(item)

        arg_names = _argument_names(node.args)
        blocked = (
            arg_names
            | collector.protected
            | collector.global_names
            | collector.nonlocal_names
        )
        if collector.has_dynamic_local_lookup:
            candidates: set[str] = set()
        else:
            candidates = {
                name
                for name in collector.bindings - blocked
                if _is_safe_rename(name)
            }
        mapping = {name: self.generator.next() for name in sorted(candidates)}
        protected = blocked | (collector.bindings - set(mapping))
        return _ScopeFrame(mapping, protected)

    def _visit_function_runtime_parts(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        node.decorator_list = [self.visit(item) for item in node.decorator_list]
        self._visit_arguments_runtime_parts(node.args)
        if node.returns:
            node.returns = self.visit(node.returns)

    def _visit_arguments_runtime_parts(self, args: ast.arguments) -> None:
        for arg in (
            list(args.posonlyargs)
            + list(args.args)
            + list(args.kwonlyargs)
        ):
            if arg.annotation:
                arg.annotation = self.visit(arg.annotation)
        if args.vararg and args.vararg.annotation:
            args.vararg.annotation = self.visit(args.vararg.annotation)
        if args.kwarg and args.kwarg.annotation:
            args.kwarg.annotation = self.visit(args.kwarg.annotation)
        args.defaults = [self.visit(item) for item in args.defaults]
        args.kw_defaults = [
            self.visit(item) if item else None for item in args.kw_defaults
        ]

    def _lambda_binding_names(self, node: ast.Lambda) -> set[str]:
        collector = _LocalBindingCollector()
        collector.visit(node.body)
        return collector.bindings


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


def obfuscate_names(tree: ast.AST) -> ast.AST:  # brutal di dalam, facade tetap aman untuk framework
    generator = _NameGenerator(tree)
    tree = _FunctionFacadeObfuscator(generator).visit(tree)
    return _ScopedNameObfuscator(generator).visit(tree)


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
    taunt_line = "# mo ngacak2 kodeku ya? selamat berpusing ria membacanya. cheers!\n"
    return (
        taunt_line
        + rev_line
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
