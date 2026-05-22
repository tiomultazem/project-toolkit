from pathlib import Path


def mob_path(source_path: Path) -> Path:  # bikin path output filemob.py
    return source_path.with_name(f"{source_path.stem}mob{source_path.suffix}")


def demob_path(source_path: Path) -> Path:  # bikin path output demfilemob.py
    return source_path.with_name(f"dem{source_path.name}")


def read_source(source_path: Path) -> str:  # baca file .py dan validasi path
    if not source_path.exists():
        raise FileNotFoundError(f"file tidak ada: {source_path}")
    if source_path.suffix != ".py":
        raise ValueError("file harus .py")
    return source_path.read_text(encoding="utf-8")