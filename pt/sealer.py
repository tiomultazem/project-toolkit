import ast
import base64
import json
import re
import zlib
from pathlib import Path

from .minifier import REV_MARKER


SEAL_MARKER_START = "# PT_SEAL_START"
SEAL_MARKER_END = "# PT_SEAL_END"


def seal_command(args: list[str]) -> int:  # handle command pt seal
    if len(args) != 3:
        print("pakai: pt seal file.json|folder/ app.py")
        return 1

    target_path, count, ignore_entry = seal_project(Path.cwd(), args[1], args[2])
    print(f"seal: {count} json -> {target_path}")
    print(f"ignore: {ignore_entry}")
    return 0


def seal_project(base_dir: Path, source_arg: str, target_arg: str) -> tuple[Path, int, str]:
    base_dir = base_dir.resolve()
    source_path = _project_path(base_dir, source_arg, "source")
    target_path = _project_path(base_dir, target_arg, "target")

    entries, ignore_entry = _collect_json_entries(base_dir, source_path)
    _validate_target(base_dir, target_path)

    block = _seal_block(entries, _root_expression(base_dir, target_path.parent))
    target_text = _read_text(target_path)
    _write_text(target_path, _inject_block(target_text, block))
    _append_gitignore(base_dir / ".gitignore", ignore_entry)
    return target_path, len(entries), ignore_entry


def _project_path(base_dir: Path, raw_path: str, label: str) -> Path:
    path = (base_dir / raw_path).resolve()
    try:
        path.relative_to(base_dir)
    except ValueError as error:
        raise ValueError(f"{label} harus berada di dalam project") from error
    return path


def _relative_path(base_dir: Path, path: Path) -> Path:
    try:
        return path.resolve().relative_to(base_dir)
    except ValueError as error:
        raise ValueError("path harus berada di dalam project") from error


def _collect_json_entries(base_dir: Path, source_path: Path) -> tuple[dict[str, str], str]:
    if not source_path.exists():
        raise FileNotFoundError(f"source tidak ada: {source_path}")

    if source_path.is_file():
        if source_path.suffix.lower() != ".json":
            raise ValueError("source file harus .json")
        files = [source_path]
        ignore_entry = _relative_path(base_dir, source_path).as_posix()
    elif source_path.is_dir():
        if source_path == base_dir:
            raise ValueError("folder project root tidak boleh diseal")
        files = sorted(path for path in source_path.rglob("*.json") if path.is_file())
        if not files:
            raise ValueError("folder tidak punya file .json")
        ignore_entry = _relative_path(base_dir, source_path).as_posix().rstrip("/") + "/"
    else:
        raise ValueError("source harus file .json atau folder")

    entries = {}
    for file_path in files:
        text = _read_text(file_path)
        json.loads(text)
        entries[_relative_path(base_dir, file_path).as_posix()] = text
    return entries, ignore_entry


def _validate_target(base_dir: Path, target_path: Path) -> None:
    if not target_path.exists() or not target_path.is_file():
        raise FileNotFoundError(f"target tidak ada: {target_path}")
    if target_path.suffix.lower() != ".py":
        raise ValueError("target harus .py")

    text = _read_text(target_path)
    if _looks_obfuscated(text):
        candidates = _real_candidates(base_dir)
        if candidates:
            joined = ", ".join(path.as_posix() for path in candidates)
            raise ValueError(f"target terlihat obfuscated/minified. edit batal. kandidat asli: {joined}")
        raise ValueError("target terlihat obfuscated/minified. edit batal. REALAPP/REALMAIN tidak ketemu")


def _looks_obfuscated(text: str) -> bool:
    return REV_MARKER in text or ("gettrace" in text and "marshal" in text and "_k=" in text)


def _real_candidates(base_dir: Path) -> list[Path]:
    candidates = []
    for path in base_dir.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        name = path.name.upper()
        if "REALAPP" in name or "REALMAIN" in name:
            candidates.append(_relative_path(base_dir, path))
    return sorted(candidates)


def _seal_block(entries: dict[str, str], root_expression: str) -> str:
    payload = _encode_entries(entries)
    chunks = _chunks(payload)
    chunk_text = ",\n    ".join(repr(chunk) for chunk in chunks)
    return f'''{SEAL_MARKER_START}
import base64 as _pt_seal_base64
import builtins as _pt_seal_builtins
import io as _pt_seal_io
import json as _pt_seal_json
import zlib as _pt_seal_zlib
from pathlib import Path as _pt_seal_Path

_pt_seal_payload = ''.join([
    {chunk_text}
])
_pt_seal_source = _pt_seal_json.loads(
    _pt_seal_zlib.decompress(
        _pt_seal_base64.b85decode(_pt_seal_payload.encode("ascii"))
    ).decode("utf-8")
)
_pt_seal_root = {root_expression}
if not hasattr(_pt_seal_builtins, "_pt_seal_data"):
    _pt_seal_builtins._pt_seal_data = {{}}
_pt_seal_builtins._pt_seal_data.update({{
    str((_pt_seal_root / _pt_name).resolve()): _pt_text
    for _pt_name, _pt_text in _pt_seal_source.items()
}})
if not hasattr(_pt_seal_builtins, "_pt_seal_original_open"):
    _pt_seal_builtins._pt_seal_original_open = _pt_seal_builtins.open
if not hasattr(_pt_seal_Path, "_pt_seal_original_open"):
    _pt_seal_Path._pt_seal_original_open = _pt_seal_Path.open
if not hasattr(_pt_seal_Path, "_pt_seal_original_read_text"):
    _pt_seal_Path._pt_seal_original_read_text = _pt_seal_Path.read_text
if not hasattr(_pt_seal_Path, "_pt_seal_original_exists"):
    _pt_seal_Path._pt_seal_original_exists = _pt_seal_Path.exists
if not hasattr(_pt_seal_Path, "_pt_seal_original_is_file"):
    _pt_seal_Path._pt_seal_original_is_file = _pt_seal_Path.is_file

def _pt_seal_key(_pt_path):
    try:
        _pt_candidate = _pt_seal_Path(_pt_path)
    except TypeError:
        return None
    if not _pt_candidate.is_absolute():
        _pt_candidate = _pt_seal_root / _pt_candidate
    try:
        return str(_pt_candidate.resolve())
    except OSError:
        return str(_pt_candidate.absolute())

def _pt_seal_read_mode(_pt_mode):
    _pt_mode = str(_pt_mode or "r")
    return "r" in _pt_mode and not any(_pt_flag in _pt_mode for _pt_flag in ("+", "w", "a", "x"))

def _pt_seal_open(_pt_file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    _pt_key = _pt_seal_key(_pt_file)
    _pt_store = _pt_seal_builtins._pt_seal_data
    if _pt_key in _pt_store and _pt_seal_read_mode(mode):
        _pt_text = _pt_store[_pt_key]
        if "b" in str(mode):
            return _pt_seal_io.BytesIO(_pt_text.encode(encoding or "utf-8"))
        return _pt_seal_io.StringIO(_pt_text)
    return _pt_seal_builtins._pt_seal_original_open(
        _pt_file, mode, buffering, encoding, errors, newline, closefd, opener
    )

def _pt_seal_path_open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
    return _pt_seal_open(self, mode, buffering, encoding, errors, newline)

def _pt_seal_path_read_text(self, encoding=None, errors=None):
    _pt_key = _pt_seal_key(self)
    if _pt_key in _pt_seal_builtins._pt_seal_data:
        return _pt_seal_builtins._pt_seal_data[_pt_key]
    return _pt_seal_Path._pt_seal_original_read_text(self, encoding=encoding, errors=errors)

def _pt_seal_path_exists(self, *args, **kwargs):
    _pt_key = _pt_seal_key(self)
    if _pt_key in _pt_seal_builtins._pt_seal_data:
        return True
    return _pt_seal_Path._pt_seal_original_exists(self, *args, **kwargs)

def _pt_seal_path_is_file(self, *args, **kwargs):
    _pt_key = _pt_seal_key(self)
    if _pt_key in _pt_seal_builtins._pt_seal_data:
        return True
    return _pt_seal_Path._pt_seal_original_is_file(self, *args, **kwargs)

_pt_seal_builtins.open = _pt_seal_open
_pt_seal_Path.open = _pt_seal_path_open
_pt_seal_Path.read_text = _pt_seal_path_read_text
_pt_seal_Path.exists = _pt_seal_path_exists
_pt_seal_Path.is_file = _pt_seal_path_is_file
{SEAL_MARKER_END}'''


def _encode_entries(entries: dict[str, str]) -> str:
    packed = json.dumps(entries, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b85encode(zlib.compress(packed, 9)).decode("ascii")


def _chunks(text: str, size: int = 76) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)]


def _root_expression(base_dir: Path, target_parent: Path) -> str:
    relative = _relative_from(target_parent.resolve(), base_dir.resolve())
    if relative in {"", "."}:
        return "_pt_seal_Path(__file__).resolve().parent"
    return f"(_pt_seal_Path(__file__).resolve().parent / {relative!r}).resolve()"


def _relative_from(start: Path, target: Path) -> str:
    parts = []
    start_parts = start.parts
    target_parts = target.parts
    index = 0
    while index < len(start_parts) and index < len(target_parts) and start_parts[index] == target_parts[index]:
        index += 1
    parts.extend(".." for _ in start_parts[index:])
    parts.extend(target_parts[index:])
    return Path(*parts).as_posix() if parts else "."


def _inject_block(text: str, block: str) -> str:
    pattern = re.compile(re.escape(SEAL_MARKER_START) + r".*?" + re.escape(SEAL_MARKER_END) + r"\n*", re.DOTALL)
    if pattern.search(text):
        return pattern.sub(block.rstrip() + "\n\n", text)

    offset = _insertion_offset(text)
    return text[:offset] + block.rstrip() + "\n\n" + text[offset:]


def _insertion_offset(text: str) -> int:
    lines = text.splitlines(keepends=True)
    index = 0
    if lines and lines[0].startswith("#!"):
        index = 1
    if len(lines) > index and re.search(r"coding[:=]\s*[-\w.]+", lines[index]):
        index += 1

    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        raise ValueError("target python tidak valid") from error

    body_index = 0
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        index = max(index, tree.body[0].end_lineno or index)
        body_index = 1

    while body_index < len(tree.body):
        node = tree.body[body_index]
        if not isinstance(node, ast.ImportFrom) or node.module != "__future__":
            break
        index = max(index, node.end_lineno or index)
        body_index += 1

    return sum(len(line) for line in lines[:index])


def _append_gitignore(path: Path, entry: str) -> None:
    if path.exists():
        text = _read_text(path)
        lines = text.splitlines()
    else:
        text = ""
        lines = []

    if entry in [line.strip() for line in lines]:
        return

    prefix = "" if not text or text.endswith("\n") else "\n"
    _write_text(path, text + prefix + entry + "\n")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
