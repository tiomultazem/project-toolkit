import re
from pathlib import Path

from .archive import decrypt_extras, encrypt_extras, get_archive_entries
from .crypto import decrypt, encrypt
from .gittools import run_git_commit, run_git_commit_one
from .minifier import REV_MARKER, make_loader, minify_source
from .paths import read_source
from .updater import updater_command
from .versioning import read_config_version, write_version


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
            "  file.py tetap file.py, tapi isinya obfuscated.",
            "  tanpa passphrase: source asli disimpan ke .pt_real/file.py.",
            "  dengan passphrase: tidak membuat .pt_real, recovery lewat pt demini.",
            "Catatan:",
            "  Untuk banyak file, pisahkan dengan koma tanpa spasi.",
            "  Spasi setelah daftar file/folder dianggap passphrase.",
            "  Passphrase opsional untuk recovery lewat pt demini.",
            "  Kalau sudah minified, user akan ditanya lanjut atau batal.",
            "  .pt_real hanya dibuat untuk mini tanpa passphrase."
        ],
        "2": [
            "PT DEMINI",
            "Decrypt hasil pt mini yang pakai passphrase.",
            "Perintah:",
            "  pt demini file.py passphrase",
            "  pt demini app.py,main.py passphrase",
            "  pt demini list.txt passphrase",
            "  pt demini folder/ passphrase",
            "Output:",
            "  file.py di path normal jadi source asli hasil decrypt.",
            "Catatan:",
            "  Passphrase wajib dan harus sama dengan saat pt mini.",
            "  Demini membaca payload terenkripsi di file obfuscated.",
            "  Listfile boleh dipisah enter atau koma.",
            "  File/folder yang gagal akan dilewati, proses lain tetap lanjut.",
        ],        "3": [
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
            "Git add, commit, lalu push ke origin main.",
            "Pakai:",
            "  pt commit pesan commit",
            "  pt commit -one file.ext pesan commit",
            "Contoh:",
            "  pt commit update readme",
            "  pt commit -one file.ext commit file.ext",
            "Yang dijalankan:",
            "  Normal: git add . lalu git commit -m pesan.",
            "  -one: git add file.ext lalu commit file itu saja.",
            "  Setelah itu push origin main.",
            "Catatan:",
            "  Semua kata setelah commit jadi pesan commit.",
            "  Untuk -one, semua kata setelah nama file jadi pesan commit.",
            "  Command jalan di folder tempat pt dipanggil.",
            "  Kalau remote origin belum ada, user akan ditanya add remote.",
            "  Kalau branch lokal masih master, akan diubah ke main saat perlu.",
        ],
        "6": [
            "PT VERSI",
            "Tulis version ke config.json di folder sekarang.",
            "Pakai awal:",
            "  pt versi x",
            "  pt versi x suffix",
            "Pakai bila config sudah punya version:",
            "  pt versi",
            "  pt versi suffix",
            "Contoh:",
            "  pt versi 1",
            "  pt versi beta",
            "Format:",
            "  x.YYMM.DD",
            "  x.YYMM.DD.suffix",
            "  x.YY.MM.DD juga auto detect kalau config lama pakai itu.",
            "Catatan:",
            "  Format versi lama auto detect; fallback tetap x.YYMM.DD.",
            "  x wajib hanya untuk versi pertama.",
            "  Key versi auto detect: version, Version, v, ver, currentVersion, dll.",
            "  Kalau key versi sudah ada, x diambil dari config.json.",
            "  suffix opsional dan tidak boleh pakai spasi.",
            "  pt versi 1 beta invalid bila config sudah punya key versi.",
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


REAL_STORE_NAME = ".pt_real"


def _real_store_root(base_dir: Path | None = None) -> Path:  # folder source asli lokal
    return (base_dir or Path.cwd()).resolve() / REAL_STORE_NAME


def _relative_project_path(path: Path, base_dir: Path | None = None) -> Path:  # path relatif dari cwd
    root = (base_dir or Path.cwd()).resolve()
    try:
        return path.resolve().relative_to(root)
    except ValueError as error:
        raise ValueError("path harus berada di dalam project") from error


def _real_store_path(source_path: Path, base_dir: Path | None = None) -> Path:  # mirror path di .pt_real
    return _real_store_root(base_dir) / _relative_project_path(source_path, base_dir)



def _is_in_real_store(path: Path, base_dir: Path | None = None) -> bool:  # jangan proses .pt_real
    relative_path = _relative_project_path(path, base_dir)
    return bool(relative_path.parts) and relative_path.parts[0] == REAL_STORE_NAME



def _looks_minified(source: str) -> bool:  # deteksi kasar file hasil mini
    return REV_MARKER in source or ("gettrace" in source and "marshal" in source and "_k=" in source)


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


def _confirm_continue(question: str) -> bool:  # tanya lanjut untuk kondisi ambigu
    answer = input(question).strip().lower()
    return answer in {"y", "yes"}


def _mini_file(source_path: Path, passphrase: str | None) -> Path:  # mini satu file, output tetap nama lama
    if _is_in_real_store(source_path):
        raise ValueError("file di .pt_real tidak boleh diminify")

    source = read_source(source_path)
    backup_path = _real_store_path(source_path)
    if _looks_minified(source):
        if not _confirm_continue("warning: sudah berupa minified. tetap lanjutkan? y/n: "):
            raise ValueError("dibatalkan")
        if backup_path.exists():
            source = backup_path.read_text(encoding="utf-8-sig")
        else:
            print("warning: backup .pt_real belum ada, backup akan memakai isi file sekarang")

    if not passphrase and not _looks_minified(source):
        _write_text(backup_path, source)
    _write_text(source_path, _make_obfuscated_text(source, passphrase))
    return source_path


def _mini_folder(folder_path: Path, passphrase: str | None) -> tuple[list[Path], list[tuple[Path, Exception]]]:  # mini folder recursive
    if not folder_path.is_dir():
        raise FileNotFoundError(f"folder tidak ada: {folder_path}")
    if _is_in_real_store(folder_path):
        raise ValueError("folder .pt_real tidak boleh diminify")

    targets = [path for path in _python_files(folder_path) if not _is_in_real_store(path)]
    if not targets:
        raise ValueError("folder tidak punya file .py")

    outputs = []
    failures = []
    for target_path in targets:
        try:
            outputs.append(_mini_file(target_path, passphrase))
        except Exception as error:
            failures.append((target_path, error))
    return outputs, failures


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


def _demini_file(source_path: Path, passphrase: str) -> Path:  # demini decrypt payload ke nama normal
    if _is_in_real_store(source_path):
        raise ValueError("folder internal PT tidak boleh didemini")

    current_source = read_source(source_path)
    payload = _reverse_payload(source_path)
    decrypted_source = decrypt(payload, passphrase)
    _write_text(source_path, decrypted_source)
    return source_path


def _demini_folder(folder_path: Path, passphrase: str) -> tuple[list[Path], list[tuple[Path, Exception]]]:  # demini folder recursive
    if not folder_path.is_dir():
        raise FileNotFoundError(f"folder tidak ada: {folder_path}")
    if _is_in_real_store(folder_path):
        raise ValueError("folder internal PT tidak boleh didemini")

    targets = [path for path in _python_files(folder_path) if not _is_in_real_store(path)]
    if not targets:
        raise ValueError("folder tidak punya file .py")

    outputs = []
    failures = []
    for target_path in targets:
        try:
            outputs.append(_demini_file(target_path, passphrase))
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
        print("atau : pt commit -one file.ext pesan commit")
        return 1

    one_file = len(args) >= 2 and args[1] == "-one"
    if one_file:
        if len(args) < 4:
            print("pakai: pt commit -one file.ext pesan commit")
            return 1
        file_path = args[2]
        message = " ".join(args[3:]).strip()
        pushed = run_git_commit_one(Path.cwd(), file_path, message)
    else:
        message = " ".join(args[1:]).strip()
        pushed = run_git_commit(Path.cwd(), message)

    if not pushed:
        print("commit dibatalkan")
        return 1
    print(f"commit pushed: {message}")
    return 0

def _config_has_version(project_dir: Path) -> bool:  # cek config punya key version
    try:
        return read_config_version(project_dir) is not None
    except Exception:
        return False


def versi_command(args: list[str]) -> int:  # handle command pt versi
    config_has_version = _config_has_version(Path.cwd())
    if config_has_version:
        if len(args) > 2:
            print("pakai: pt versi [suffix]")
            print("config.json sudah punya version, angka utama diambil otomatis")
            return 1
        suffix = args[1] if len(args) == 2 else None
        version = write_version(Path.cwd(), None, suffix)
    else:
        if len(args) not in {2, 3}:
            print("pakai: pt versi x [suffix]")
            return 1
        suffix = args[2] if len(args) == 3 else None
        version = write_version(Path.cwd(), args[1], suffix)

    print(f"version: {version}")
    return 0
