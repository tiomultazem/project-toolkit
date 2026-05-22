from pathlib import Path

from .archive import decrypt_extras, encrypt_extras, get_archive_entries
from .crypto import decrypt, encrypt
from .gittools import run_git_commit
from .minifier import REV_MARKER, make_loader, minify_source
from .paths import demob_path, mob_path, read_source


def show_help() -> int:  # tampilkan bantuan command untuk user
    print("+------------------------------------------------------------+")
    print("| PT - Python Project Toolkit                         v1.0   |")
    print("| 2026 | Made with <3 by Gilang Wahyu Prasetyo               |")
    print("| (c) BPS Kabupaten Tabalong                                 |")
    print("+------------------------------------------------------------+")
    print("| 1. pt mini    -> minify file Python                        |")
    print("| 2. pt demini  -> deminify file Python                      |")
    print("| 3. pt enkrip  -> enkripsi kumpulan file/folder             |")
    print("| 4. pt dekrip  -> dekripsi kumpulan file/folder             |")
    print("| 5. pt commit  -> git add, commit, push main                |")
    print("+------------------------------------------------------------+")
    print("Ketik: pt [1-5] untuk detail command. Contoh: pt 5")
    return 1


def detail_help(menu: str) -> int:  # tampilkan detail command pilihan user
    details = {
        "1": [
            "PT MINI",
            "Minify + obfuscate file Python.",
            "Pakai:",
            "  pt mini file.py",
            "  pt mini file.py passphrase",
            "Beda:",
            "  Tanpa passphrase: filemob.py tidak bisa dibalik.",
            "  Dengan passphrase: filemob.py bisa dibalik pakai pt demini.",
            "Output:",
            "  filemob.py di folder file.py berada",
            "Catatan:",
            "  Passphrase bebas/custom, tapi tidak boleh pakai spasi.",
        ],
        "2": [
            "PT DEMINI",
            "Balikin hasil pt mini yang pakai passphrase.",
            "Pakai:",
            "  pt demini filemob.py passphrase",
            "Output:",
            "  demfilemob.py di folder filemob.py berada",
            "Catatan:",
            "  Ini hanya untuk hasil pt mini file.py passphrase.",
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
            "  extras.mwehe di folder sekarang",
            "Catatan:",
            "  Passphrase bebas/custom, tapi tidak boleh pakai spasi.",
            "  File apa saja bisa: .env, .jpg, .png, .xlsx, dll.",
            "  Folder boleh ditulis static/ biar jelas.",
        ],
        "4": [
            "PT DEKRIP",
            "Dekripsi extras.mwehe ke folder sekarang.",
            "Pakai:",
            "  pt dekrip passphrase",
            "Input:",
            "  extras.mwehe harus ada di folder sekarang",
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


def mini_command(args: list[str]) -> int:  # handle command pt mini
    if len(args) < 2:
        return show_help()

    source_path = Path(args[1]).resolve()
    if len(args) > 3:
        print("warning: passphrase tidak boleh pake spasi")
        return 1

    passphrase = args[2] if len(args) == 3 else None
    if passphrase and _passphrase_has_space(passphrase):
        print("warning: passphrase tidak boleh pake spasi")
        return 1

    source = read_source(source_path)
    minified = minify_source(source)
    reversible_payload = encrypt(source, passphrase) if passphrase else None
    output_path = mob_path(source_path)
    output_path.write_text(
        make_loader(minified, reversible_payload),
        encoding="utf-8",
        newline="\n",
    )
    print(f"jadi: {output_path}")
    return 0


def demini_command(args: list[str]) -> int:  # handle command pt demini
    if len(args) != 3:
        print("pakai: pt demini filemob.py passphrase")
        return 1

    source_path = Path(args[1]).resolve()
    passphrase = args[2]
    if _passphrase_has_space(passphrase):
        print("warning: passphrase tidak boleh pake spasi")
        return 1

    text = read_source(source_path)
    payload = None
    for line in text.splitlines():
        if line.startswith(REV_MARKER):
            payload = line.removeprefix(REV_MARKER).strip()
            break

    if not payload:
        print("file ini tidak punya payload reverse")
        return 1

    output_path = demob_path(source_path)
    output_path.write_text(decrypt(payload, passphrase), encoding="utf-8", newline="\n")
    print(f"jadi: {output_path}")
    return 0


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