import io
import re
import tarfile
import zlib
from pathlib import Path

from .crypto import decrypt_bytes, encrypt_bytes


ARCHIVE_NAME = "extras.ptk"
MAGIC = "PTK1"


def split_entries(text: str) -> list[str]:  # pecah input koma/baris jadi list path
    raw_entries = re.split(r"[,\r\n]+", text)
    entries = []
    for entry in raw_entries:
        cleaned = entry.strip().strip('"').strip("'")
        if cleaned:
            entries.append(cleaned)
    return entries


def safe_entry_path(base_dir: Path, entry: str, check_exists: bool = True) -> tuple[Path, str]:  # validasi entry tetap di folder aktif
    cleaned = entry.rstrip("/\\")
    if not cleaned:
        raise ValueError("path kosong")
    if Path(cleaned).is_absolute():
        raise ValueError(f"path harus relatif: {entry}")

    base = base_dir.resolve()
    path = (base / cleaned).resolve()
    try:
        path.relative_to(base)
    except ValueError as error:
        raise ValueError(f"path keluar folder kerja: {entry}") from error

    if check_exists and not path.exists():
        raise FileNotFoundError(f"file/folder tidak ada: {entry}")
    return path, Path(cleaned).as_posix()


def get_archive_entries(base_dir: Path, listfile: Path | None) -> list[str]:  # ambil daftar file/folder untuk archive
    if listfile:
        if not listfile.exists():
            raise FileNotFoundError(f"listfile tidak ada: {listfile}")
        text = listfile.read_text(encoding="utf-8")
    else:
        text = input("file/folder dipisah koma: ")

    entries = split_entries(text)
    if not entries:
        raise ValueError("input file/folder kosong")

    # If only exclusions are provided, default to "." (all) first
    has_inclusion = any(not entry.startswith("!") for entry in entries)
    if not has_inclusion:
        entries.insert(0, ".")

    for entry in entries:
        if entry.startswith("!"):
            safe_entry_path(base_dir, entry[1:], check_exists=False)
        else:
            safe_entry_path(base_dir, entry)
    return entries


def build_tar_bytes(base_dir: Path, entries: list[str]) -> bytes:  # bungkus file/folder jadi tar bytes
    inclusions = []
    exclusions = []
    for entry in entries:
        if entry.startswith("!"):
            exclusions.append(entry[1:])
        else:
            inclusions.append(entry)

    # Normalize exclusions to relative paths without leading ./ or backslashes
    def normalize_rel_path(p: str) -> str:
        p = p.replace("\\", "/")
        parts = p.split("/")
        cleaned_parts = [part for part in parts if part and part != "."]
        return "/".join(cleaned_parts)

    normalized_excludes = []
    for exc in exclusions:
        _, rel_path = safe_entry_path(base_dir, exc, check_exists=False)
        normalized_excludes.append(normalize_rel_path(rel_path))

    def exclude_filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
        norm_name = normalize_rel_path(tarinfo.name)
        for exc in normalized_excludes:
            if norm_name == exc or norm_name.startswith(exc + "/"):
                return None
        return tarinfo

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for entry in inclusions:
            source_path, archive_name = safe_entry_path(base_dir, entry)
            archive.add(source_path, arcname=archive_name, recursive=True, filter=exclude_filter)
    return buffer.getvalue()


def encrypt_extras(base_dir: Path, entries: list[str], passphrase: str) -> Path:  # buat extras.ptk terenkripsi
    output_path = base_dir / ARCHIVE_NAME
    tar_bytes = build_tar_bytes(base_dir, entries)
    compressed = zlib.compress(tar_bytes, 9)
    payload = encrypt_bytes(compressed, passphrase)
    output_path.write_text(f"{MAGIC}\n{payload}\n", encoding="utf-8", newline="\n")
    return output_path


def assert_safe_member(base_dir: Path, member: tarfile.TarInfo) -> None:  # cegah ekstrak keluar folder
    target = (base_dir / member.name).resolve()
    try:
        target.relative_to(base_dir.resolve())
    except ValueError as error:
        raise ValueError(f"isi archive berbahaya: {member.name}") from error


def decrypt_extras(base_dir: Path, passphrase: str) -> None:  # ekstrak extras.ptk ke folder sekarang
    archive_path = base_dir / ARCHIVE_NAME
    if not archive_path.exists():
        raise FileNotFoundError(f"archive tidak ada: {archive_path}")

    lines = archive_path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2 or lines[0] != MAGIC:
        raise ValueError("format extras.ptk tidak valid")

    compressed = decrypt_bytes(lines[1], passphrase)
    tar_bytes = zlib.decompress(compressed)
    buffer = io.BytesIO(tar_bytes)
    with tarfile.open(fileobj=buffer, mode="r:") as archive:
        for member in archive.getmembers():
            assert_safe_member(base_dir, member)
        archive.extractall(base_dir)