import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


CONFIG_NAME = "config.json"
CHANGELOG_NAME = "changelog.json"


@dataclass(frozen=True)
class VersionParts:
    major: int
    year: int
    month_day: int
    suffix: str

    @property
    def number(self) -> tuple[int, int, int]:
        return self.major, self.year, self.month_day


def date_now() -> datetime:  # tanggal sekarang
    return datetime.now()


def build_version(major: str, suffix: str | None = None) -> str:  # bikin nomor versi baru
    if not major.isdigit():
        raise ValueError("x wajib angka")
    now = date_now()
    base = f"{int(major)}.{now:%y}.{now:%m%d}"
    return f"{base}.{suffix}" if suffix else base


def parse_version(version: str) -> VersionParts:  # pecah versi jadi bagian pembanding
    parts = version.split(".")
    if len(parts) not in {3, 4}:
        raise ValueError(f"format versi tidak valid: {version}")
    major, year, month_day = parts[:3]
    if not major.isdigit() or not year.isdigit() or not month_day.isdigit():
        raise ValueError(f"format versi tidak valid: {version}")
    suffix = parts[3] if len(parts) == 4 else ""
    return VersionParts(int(major), int(year), int(month_day), suffix)


def load_json(path: Path, default: dict) -> dict:  # baca json atau default
    if not path.exists():
        return default.copy()
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:  # tulis json rapi
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def ask_changelog(version: str) -> list[str]:  # input changelog multiline
    print(f"changelog untuk {version}:")
    print("enter kosong untuk selesai")
    lines = []
    while True:
        line = input(f"{len(lines) + 1}> ").strip()
        if not line:
            break
        lines.append(line)
    return lines


def should_write_changelog(old_version: str | None, new_version: str) -> bool:  # cek perlu changelog
    if not old_version:
        return True
    old_parts = parse_version(old_version)
    new_parts = parse_version(new_version)

    if old_parts.number > new_parts.number:
        raise ValueError(f"versi sekarang {old_version} lebih besar dari {new_version}")
    if old_parts.number == new_parts.number and old_parts.suffix == new_parts.suffix:
        raise ValueError(f"anda sudah membuat versi {new_version} hari ini.")
    return old_parts.number < new_parts.number or old_parts.suffix != new_parts.suffix


def current_major(version: str) -> str:  # ambil angka utama dari versi lama
    parts = parse_version(version)
    return str(parts.major)


def write_version(project_dir: Path, major: str | None = None, suffix: str | None = None) -> str:  # tulis config dan changelog
    if suffix and any(char.isspace() for char in suffix):
        raise ValueError("suffix tidak boleh pakai spasi")

    config_path = project_dir / CONFIG_NAME
    changelog_path = project_dir / CHANGELOG_NAME
    config = load_json(config_path, {})
    old_version = config.get("version")
    if old_version:
        major = current_major(str(old_version))
    elif not major:
        raise ValueError("x wajib angka untuk versi pertama")

    new_version = build_version(major, suffix)

    if should_write_changelog(old_version, new_version):
        changelog = load_json(changelog_path, {})
        changelog[new_version] = ask_changelog(new_version)
        write_json(changelog_path, changelog)

    config["version"] = new_version
    write_json(config_path, config)
    return new_version