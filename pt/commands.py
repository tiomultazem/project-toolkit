import re
from pathlib import Path

from .archive import decrypt_extras, encrypt_extras, get_archive_entries
from .crypto import decrypt, encrypt
from .gittools import run_git_commit
from .minifier import REV_MARKER, make_loader, minify_source
from .paths import read_source
from .updater import updater_command
from .versioning import write_version


def show_help() -> int:  # tampilkan bantuan command untuk user
    print("+------------------------------------------------------------+")
    print("| PT - Python Project Toolkit                         v1.0   |")
    print("| 2026 | Made with <3 by Gilang Wahyu Prasetyo               |")
    print("| (c) BPS Kabupaten Tabalong                                 |")
    print("+------------------------------------------------------------+")
    print("| 1. pt mini    -> minify file Python                        |")
    print("| 2. pt demini  -> deminify file hasil mini                  |")
    print("| 3. pt enkrip  -> enkripsi kumpulan file/folder             |")
    print("| 4. pt dekrip  -> dekripsi kumpulan file/folder             |")
    print("| 5. pt commit  -> git add, commit, push main                |")
    print("| 6. pt versi   -> tulis versi dan changelog                 |")
    print("| 7. pt updater -> inject updater project                    |")
    print("+------------------------------------------------------------+")
    print("Ketik: pt [1-7] untuk detail command. Contoh: pt 7")
    return 1

def detail_help(menu: str) -> int:  # tampilkan detail command pilihan user
    details = {
        "1": [
            "PT MINI",
            "Hard minify + obfuscate file Python.",
            "Perintah:",
            "  pt mini file.py",
            "  pt mini file.py passphrase",
            "  pt mini app.py,main.py,utils.py",
            "  pt mini app.py,main.py passphrase",
            "  pt mini list.txt",
            "  pt mini list.txt passphrase",
            "  pt mini folder/",
            "  pt mini folder/ passphrase",
            "Output:",
            "  file.py -> realfile.py, lalu file.py jadi obfuscated",
            "  folder/ -> realfolder/, lalu folder/ jadi obfuscated",
            "Catatan:",
            "  Untuk banyak file, pisahkan dengan koma tanpa spasi.",
            "  Spasi setelah daftar file/folder dianggap passphrase.",
            "  Passphrase berlaku untuk semua file.",
            "  Dengan passphrase: output bisa dibalik pakai pt demini.",
        ],
        "2": [
            "PT DEMINI",
            "Deminify hasil pt mini yang pakai passphrase.",
            "Perintah:",
            "  pt demini file.py passphrase",
            "  pt demini app.py,main.py passphrase",
            "  pt demini list.txt passphrase",
            "  pt demini folder/ passphrase",
            "Output:",
            "  file.py -> realfile.py",
            "  folder/ -> realfolder/realfile.py",
            "Catatan:",
            "  Ini hanya untuk hasil pt mini yang pakai passphrase.",
            "  Banyak file dipisah koma tanpa spasi.",
            "  Listfile boleh dipisah enter atau koma.",
            "  Passphrase harus sama dengan saat pt mini.",
        ],
        "3": [
            "PT ENKRIP",
            "Enkripsi kumpulan file/folder dari folder sekarang.",
            "Cara 1 - input manual:",
            "  pt enkrip passphrase",
            "  Setelah enter, ketik daftar file/folder dipisah koma.",
            "  Contoh input: .env,app.py,static/",
            "Cara 2 - pakai listfile:",
            "  pt enkrip passphrase listfile.txt",
            "  Daftar file/folder dibaca dari listfile.txt.",
            "  Isi listfile boleh dipisah enter atau koma.",
            "Output:",
            "  extras.ptk di folder sekarang",
            "Catatan:",
            "  Passphrase bebas/custom, tapi tidak boleh pakai spasi.",
            "  File apa saja bisa: .env, .jpg, .png, .xlsx, dll.",
            "  Folder boleh ditulis static/ biar jelas.",
        ],
        "4": [
            "PT DEKRIP",
            "Dekripsi extras.ptk ke folder sekarang.",
            "Pakai:",
            "  pt dekrip passphrase",
            "Input:",
            "  extras.ptk harus ada di folder sekarang",
            "Catatan:",
            "  Pakai passphrase yang sama saat pt enkrip.",
            "  Passphrase bebas/custom, tapi tidak boleh pakai spasi.",
        ],
        "5": [
            "PT COMMIT",
            "Git add semua perubahan, commit, lalu push ke origin main.",
            "Pakai:",
            "  pt commit pesan commit",
            "Contoh:",
            "  pt commit update readme",
            "Yang dijalankan:",
            "  git add .",
            "  git commit -m \"update readme\"",
            "  git push origin main",
            "Catatan:",
            "  Semua kata setelah commit jadi pesan commit.",
            "  Command jalan di folder tempat pt dipanggil.",
            "  Kalau remote origin belum ada, user akan ditanya add remote.",
            "  Default remote: origin. Default branch: main.",
            "  Kalau branch lokal masih master, akan diubah ke main saat perlu.",
            "  Kalau sudah staged, langsung commit dan push.",
            "  Kalau sudah commit, langsung push saja.",
        ],
        "6": [
            "PT VERSI",
            "Tulis version ke config.json di folder sekarang.",
            "Pakai:",
            "  pt versi x",
            "  pt versi x suffix",
            "Contoh:",
            "  pt versi 1",
            "  pt versi 1 beta",
            "Format:",
            "  x.YY.MMDD",
            "  x.YY.MMDD.suffix",
            "Catatan:",
            "  x wajib angka.",
            "  suffix opsional dan tidak boleh pakai spasi.",
            "  Kalau versi baru, changelog ditulis ke changelog.json.",
        ],
        "7": [
            "PT UPDATER",
            "Inject updater otomatis project.",
            "Pakai:",
            "  pt updater flask main.py templates/index.html",
            "  pt updater ctk main.py",
            "Flask:",
            "  Membuat pt_update_core.py.",
            "  Inject route backend ke main.py.",
            "  Inject SweetAlert ke index.html.",
            "CTk:",
            "  Membuat updater.py sebagai jendela updater.",
            "  Inject pemanggil updater ke main.py.",
            "Wajib:",
            "  Repo GitHub public di remote origin branch main.",
            "  config.json dan changelog.json ada di repo.",
            "  Project lokal punya config.json.",
            "Alur:",
            "  Cek versi remote, tampilkan changelog.",
            "  Jika user setuju, download zip, extract, replace.",
            "  Hapus zip/temp, lalu rerun aplikasi.",
        ],
    }
    lines = details[menu]
    print("+------------------------------------------------------------+")
    print(f"| {lines[0]:<58} |")
    print("+------------------------------------------------------------+")
    for line in lines[1:]:
        print(line)
    return 0

def _passphrase_has_space(passphrase: str) -> bool:  # cek passphrase mengandung spasi
    return any(char.isspace() for char in passphrase)


def _real_path(path: Path) -> Path:  # bikin path dengan prefix real
    return path.with_name(f"real{path.name}")


def _split_entries(text: str, strict_commas: bool = False) -> list[str]:  # pecah input koma/baris
    raw_entries = re.split(r"[,\r\n]+", text)
    if strict_commas and "," in text and any(not entry.strip() for entry in raw_entries):
        raise ValueError("pisahkan file dengan koma tanpa spasi. Spasi dianggap passphrase")

    entries = []
    for entry in raw_entries:
        cleaned = entry.strip().strip('"').strip("'")
        if cleaned:
            entries.append(cleaned)
    return entries


def _input_sources(base_dir: Path, input_arg: str) -> list[Path]:  # ambil daftar file/folder dari argumen/listfile
    input_path = (base_dir / input_arg).resolve()
    if input_path.suffix.lower() == ".txt" and input_path.exists():
        entries = _split_entries(input_path.read_text(encoding="utf-8-sig"))
    else:
        entries = _split_entries(input_arg, strict_commas=True)

    if not entries:
        raise ValueError("input kosong")
    return [(base_dir / entry).resolve() for entry in entries]


def _python_files(folder_path: Path) -> list[Path]:  # ambil semua file .py di folder
    return sorted(path for path in folder_path.rglob("*.py") if path.is_file())


def _make_obfuscated_text(source: str, passphrase: str | None) -> str:  # bikin isi file obfuscated
    minified = minify_source(source)
    reversible_payload = encrypt(source, passphrase) if passphrase else None
    return make_loader(minified, reversible_payload)


def _write_text(path: Path, text: str) -> None:  # tulis file utf-8 lf
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _mini_file(source_path: Path, passphrase: str | None) -> Path:  # mini satu file: asli jadi real*, output pakai nama lama
    real_path = _real_path(source_path)
    if real_path.exists():
        raise FileExistsError(f"file asli sudah ada: {real_path}")

    source = read_source(source_path)
    obfuscated = _make_obfuscated_text(source, passphrase)
    source_path.replace(real_path)
    _write_text(source_path, obfuscated)
    return source_path


def _mini_folder(folder_path: Path, passphrase: str | None) -> list[Path]:  # mini folder: asli jadi realfolder, output pakai folder lama
    if not folder_path.is_dir():
        raise FileNotFoundError(f"folder tidak ada: {folder_path}")

    real_folder = _real_path(folder_path)
    if real_folder.exists():
        raise FileExistsError(f"folder asli sudah ada: {real_folder}")

    targets = _python_files(folder_path)
    if not targets:
        raise ValueError("folder tidak punya file .py")

    outputs = []
    payloads = []
    for target_path in targets:
        source = read_source(target_path)
        relative_path = target_path.relative_to(folder_path)
        payloads.append((relative_path, _make_obfuscated_text(source, passphrase)))

    folder_path.replace(real_folder)
    folder_path.mkdir(parents=True, exist_ok=True)
    for relative_path, obfuscated in payloads:
        output_path = folder_path / relative_path
        _write_text(output_path, obfuscated)
        outputs.append(output_path)
    return outputs


def _run_batch(source_paths: list[Path], action) -> int:  # proses banyak file/folder, gagal sebagian lanjut
    successes = []
    failures = []
    for source_path in source_paths:
        try:
            result = action(source_path)
            action_failures = []
            if isinstance(result, tuple):
                output_paths, action_failures = result
            else:
                output_paths = result
            if isinstance(output_paths, Path):
                output_paths = [output_paths]
            successes.extend(output_paths)
            failures.extend(action_failures)
            for output_path in output_paths:
                print(f"jadi: {output_path}")
            for failed_path, error in action_failures:
                print(f"gagal: {failed_path} -> {error}")
        except Exception as error:
            failures.append((source_path, error))
            print(f"gagal: {source_path} -> {error}")

    if successes:
        print(f"sukses: {len(successes)} file")
    if failures:
        print(f"gagal: {len(failures)} input")
        for source_path, error in failures:
            print(f"- {source_path}: {error}")
        return 1
    return 0


def mini_command(args: list[str]) -> int:  # handle command pt mini
    if len(args) < 2:
        return show_help()
    if len(args) > 3:
        print("warning: pisahkan file dengan koma tanpa spasi. Spasi dianggap passphrase.")
        return 1

    passphrase = args[2] if len(args) == 3 else None
    if passphrase and passphrase.lower().endswith(".py"):
        print("warning: pisahkan file dengan koma tanpa spasi. Spasi dianggap passphrase.")
        return 1
    if passphrase and _passphrase_has_space(passphrase):
        print("warning: passphrase tidak boleh pake spasi")
        return 1

    try:
        source_paths = _input_sources(Path.cwd(), args[1])
    except ValueError as error:
        if "pisahkan file" in str(error):
            print("warning: pisahkan file dengan koma tanpa spasi. Spasi dianggap passphrase.")
            return 1
        raise

    def action(source_path: Path) -> list[Path] | Path:
        if source_path.is_dir():
            return _mini_folder(source_path, passphrase)
        return _mini_file(source_path, passphrase)

    return _run_batch(source_paths, action)


def _reverse_payload(source_path: Path) -> str:  # ambil payload reverse dari file hasil mini passphrase
    text = read_source(source_path)
    for line in text.splitlines():
        if line.startswith(REV_MARKER):
            return line.removeprefix(REV_MARKER).strip()
    raise ValueError("file ini tidak punya payload reverse")


def _demini_output_path(source_path: Path, root_dir: Path | None = None) -> Path:  # output demini pakai prefix real
    if root_dir is None:
        return _real_path(source_path)
    relative_path = source_path.relative_to(root_dir)
    return _real_path(root_dir) / relative_path.with_name(f"real{relative_path.name}")


def _demini_file(source_path: Path, passphrase: str, root_dir: Path | None = None) -> Path:  # demini satu file
    output_path = _demini_output_path(source_path, root_dir)
    payload = _reverse_payload(source_path)
    _write_text(output_path, decrypt(payload, passphrase))
    return output_path


def _demini_folder(folder_path: Path, passphrase: str) -> tuple[list[Path], list[tuple[Path, Exception]]]:  # demini folder recursive
    if not folder_path.is_dir():
        raise FileNotFoundError(f"folder tidak ada: {folder_path}")

    targets = [path for path in _python_files(folder_path) if not path.name.startswith("real")]
    if not targets:
        raise ValueError("folder tidak punya file .py")

    outputs = []
    failures = []
    for target_path in targets:
        try:
            outputs.append(_demini_file(target_path, passphrase, folder_path))
        except Exception as error:
            failures.append((target_path, error))
    return outputs, failures


def demini_command(args: list[str]) -> int:  # handle command pt demini
    if len(args) != 3:
        print("pakai: pt demini file.py|folder/|list.txt passphrase")
        return 1

    passphrase = args[2]
    if _passphrase_has_space(passphrase):
        print("warning: passphrase tidak boleh pake spasi")
        return 1

    try:
        source_paths = _input_sources(Path.cwd(), args[1])
    except ValueError as error:
        if "pisahkan file" in str(error):
            print("warning: pisahkan file dengan koma tanpa spasi. Spasi dianggap passphrase.")
            return 1
        raise

    def action(source_path: Path) -> list[Path] | Path:
        if source_path.is_dir():
            return _demini_folder(source_path, passphrase)
        return _demini_file(source_path, passphrase)

    return _run_batch(source_paths, action)

def enkrip_command(args: list[str]) -> int:  # handle command pt enkrip
    if len(args) not in {2, 3}:
        print("pakai: pt enkrip passphrase [listfile.txt]")
        return 1

    passphrase = args[1]
    if _passphrase_has_space(passphrase):
        print("warning: passphrase tidak boleh pake spasi")
        return 1

    listfile = Path(args[2]).resolve() if len(args) == 3 else None
    entries = get_archive_entries(Path.cwd(), listfile)
    output_path = encrypt_extras(Path.cwd(), entries, passphrase)
    print(f"jadi: {output_path}")
    return 0


def dekrip_command(args: list[str]) -> int:  # handle command pt dekrip
    if len(args) != 2:
        print("pakai: pt dekrip passphrase")
        return 1

    passphrase = args[1]
    if _passphrase_has_space(passphrase):
        print("warning: passphrase tidak boleh pake spasi")
        return 1

    decrypt_extras(Path.cwd(), passphrase)
    print(f"selesai ekstrak: {Path.cwd()}")
    return 0


def commit_command(args: list[str]) -> int:  # handle command pt commit
    if len(args) < 2:
        print("pakai: pt commit pesan commit")
        return 1

    message = " ".join(args[1:]).strip()
    pushed = run_git_commit(Path.cwd(), message)
    if not pushed:
        print("commit dibatalkan")
        return 1
    print(f"commit pushed: {message}")
    return 0

def versi_command(args: list[str]) -> int:  # handle command pt versi
    if len(args) not in {2, 3}:
        print("pakai: pt versi x [suffix]")
        return 1

    suffix = args[2] if len(args) == 3 else None
    version = write_version(Path.cwd(), args[1], suffix)
    print(f"version: {version}")
    return 0