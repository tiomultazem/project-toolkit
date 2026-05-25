import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


CONFIG_NAME = "config.json"
CHANGELOG_NAME = "changelog.json"
DEFAULT_VERSION_KEY = "version"
VERSION_FORMAT_YYMM_DD = "yymm.dd"
VERSION_FORMAT_YY_MMDD = "yy.mmdd"
VERSION_FORMAT_YY_MM_DD = "yy.mm.dd"
DEFAULT_VERSION_FORMAT = VERSION_FORMAT_YYMM_DD
VERSION_KEY_CANDIDATES = (
    "version",
    "Version",
    "VERSION",
    "v",
    "V",
    "ver",
    "Ver",
    "VER",
    "currentVersion",
    "current_version",
    "currentVer",
    "current_ver",
    "CurrentVersion",
    "CURRENT_VERSION",
    "appVersion",
    "app_version",
    "appVer",
    "app_ver",
    "AppVersion",
    "APP_VERSION",
    "projectVersion",
    "project_version",
    "projectVer",
    "project_ver",
    "ProjectVersion",
    "PROJECT_VERSION",
    "versionName",
    "version_name",
    "versionNumber",
    "version_number",
    "releaseVersion",
    "release_version",
    "releaseVer",
    "release_ver",
    "latestVersion",
    "latest_version",
    "latestVer",
    "latest_ver",
)
_VERSION_KEY_ALIASES = {
    re.sub(r"[^a-z0-9]", "", key.lower()) for key in VERSION_KEY_CANDIDATES
}
_VERSION_KEY_DENY_SUFFIXES = ("code", "id", "hash", "checksum")


@dataclass(frozen=True)
class VersionParts:
    major: int
    year: int
    month: int
    day: int
    suffix: str

    @property
    def number(self) -> tuple[int, int, int, int]:
        return self.major, self.year, self.month, self.day


def date_now() -> datetime:  # tanggal sekarang
    return datetime.now()


def build_version(
    major: str,
    suffix: str | None = None,
    version_format: str = DEFAULT_VERSION_FORMAT,
) -> str:  # bikin nomor versi baru
    if not major.isdigit():
        raise ValueError("x wajib angka")
    now = date_now()
    if version_format == VERSION_FORMAT_YY_MMDD:
        base = f"{int(major)}.{now:%y}.{now:%m%d}"
    elif version_format == VERSION_FORMAT_YY_MM_DD:
        base = f"{int(major)}.{now:%y}.{now:%m}.{now:%d}"
    else:
        base = f"{int(major)}.{now:%y%m}.{now:%d}"
    return f"{base}.{suffix}" if suffix else base


def detect_version_format(version: str | None) -> str:  # deteksi format versi lama
    if not version:
        return DEFAULT_VERSION_FORMAT
    parts = str(version).split(".")
    if len(parts) not in {3, 4, 5}:
        return DEFAULT_VERSION_FORMAT

    if _is_yy_mm_dd_parts(parts):
        return VERSION_FORMAT_YY_MM_DD

    second, third = parts[1:3]
    if second.isdigit() and third.isdigit() and len(second) == 2 and len(third) == 4:
        return VERSION_FORMAT_YY_MMDD
    return DEFAULT_VERSION_FORMAT


def _valid_month_day(month: int, day: int) -> bool:  # cek tanggal kasar
    return 1 <= month <= 12 and 1 <= day <= 31


def _is_yy_mm_dd_parts(parts: list[str]) -> bool:  # cek format x.yy.mm.dd
    if len(parts) == 4:
        major, year, month, day = parts
    elif len(parts) == 5:
        major, year, month, day, suffix = parts
    else:
        return False
    if not (major.isdigit() and year.isdigit() and month.isdigit() and day.isdigit()):
        return False
    if len(year) != 2 or len(month) not in {1, 2} or len(day) not in {1, 2}:
        return False
    return _valid_month_day(int(month), int(day))


def _parse_yy_mm_dd(parts: list[str], version: str) -> VersionParts:  # parse x.yy.mm.dd
    major, year, month, day = parts[:4]
    if not _is_yy_mm_dd_parts(parts):
        raise ValueError(f"format versi tidak valid: {version}")
    suffix = parts[4] if len(parts) == 5 else ""
    return VersionParts(int(major), int(year), int(month), int(day), suffix)


def _parse_version_date(second: str, third: str, version: str) -> tuple[int, int, int]:  # support format lama/baru
    if len(second) == 4 and len(third) in {1, 2}:
        year = int(second[:2])
        month = int(second[2:])
        day = int(third)
    elif len(second) == 2 and len(third) == 4:
        year = int(second)
        month = int(third[:2])
        day = int(third[2:])
    else:
        raise ValueError(f"format versi tidak valid: {version}")

    if not _valid_month_day(month, day):
        raise ValueError(f"format versi tidak valid: {version}")
    return year, month, day


def parse_version(version: str) -> VersionParts:  # pecah versi jadi bagian pembanding
    parts = version.split(".")
    if len(parts) not in {3, 4, 5}:
        raise ValueError(f"format versi tidak valid: {version}")

    if _is_yy_mm_dd_parts(parts):
        return _parse_yy_mm_dd(parts, version)

    if len(parts) == 5:
        raise ValueError(f"format versi tidak valid: {version}")

    major, second, third = parts[:3]
    if not major.isdigit() or not second.isdigit() or not third.isdigit():
        raise ValueError(f"format versi tidak valid: {version}")
    year, month, day = _parse_version_date(second, third, version)
    suffix = parts[3] if len(parts) == 4 else ""
    return VersionParts(int(major), year, month, day, suffix)


def load_json(path: Path, default: dict) -> dict:  # baca json atau default
    if not path.exists():
        return default.copy()
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict) -> None:  # tulis json rapi
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _normalize_key(key: str) -> str:  # samakan style key config
    return re.sub(r"[^a-z0-9]", "", key.lower())


def _key_words(key: str) -> list[str]:  # pecah snake/camel/kebab key
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", key)
    return [
        word.lower()
        for word in re.split(r"[^A-Za-z0-9]+", spaced)
        if word
    ]


def _has_value(value) -> bool:  # cek value versi tidak kosong
    return value is not None and str(value).strip() != ""


def _looks_like_version_key(key: str) -> bool:  # deteksi nama key versi umum
    normalized = _normalize_key(key)
    if normalized in _VERSION_KEY_ALIASES:
        return True
    words = _key_words(key)
    if normalized.endswith(_VERSION_KEY_DENY_SUFFIXES) or (
        words and words[-1] in _VERSION_KEY_DENY_SUFFIXES
    ):
        return False
    if "version" in words or "ver" in words:
        return True
    return False


def find_version_key(config: dict, require_value: bool = False) -> str | None:  # cari key versi
    for key in VERSION_KEY_CANDIDATES:
        if key in config and (not require_value or _has_value(config[key])):
            return key
    for key, value in config.items():
        if not isinstance(key, str) or not _looks_like_version_key(key):
            continue
        if require_value and not _has_value(value):
            continue
        return key
    return None


def config_version(config: dict) -> str | None:  # ambil versi dari key yang terdeteksi
    version_key = find_version_key(config, require_value=True)
    if not version_key:
        return None
    return str(config[version_key])


def read_config_version(project_dir: Path) -> str | None:  # baca versi dari config.json
    return config_version(load_json(project_dir / CONFIG_NAME, {}))


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
    version_key = (
        find_version_key(config, require_value=True)
        or find_version_key(config)
        or DEFAULT_VERSION_KEY
    )
    old_version = config.get(version_key)
    if old_version:
        major = current_major(str(old_version))
    elif not major:
        raise ValueError("x wajib angka untuk versi pertama")

    new_version = build_version(major, suffix, detect_version_format(old_version))

    if should_write_changelog(old_version, new_version):
        changelog = load_json(changelog_path, {})
        changelog[new_version] = ask_changelog(new_version)
        write_json(changelog_path, changelog)

    config[version_key] = new_version
    write_json(config_path, config)
    return new_version
