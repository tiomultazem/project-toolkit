# Project Toolkit

`pt` adalah command-line toolkit untuk bantu manage project dari direktori mana pun.

Belakangan ini aku nyadar aku nyepam file-file yang sama di setiap project. Obfuscator, minifier-deminifier, decryptor-encryptor.

Trus tiba-tiba sambil melamun aku dapet ilham: kenapa ga kujadikan satu tools aja yang ga perlu ku-push ke setiap repo?

Lalu dibuatlah project ini.

---


## Isi sekarang

- `mini`: hard minify + obfuscate file Python
- `demini`: balikin hasil `mini` yang pakai passphrase
- `enkrip`: enkripsi kumpulan file/folder ke `extras.ptk`
- `dekrip`: dekripsi `extras.ptk` ke folder sekarang
- `commit`: git add, commit, lalu push ke `origin main`
- `versi`: tulis versi project ke `config.json` dan changelog ke `changelog.json`
- `updater`: rencana injeksi updater otomatis untuk Flask/CTk

Kamu boleh usul nambah fitur dengan chat aku.

---

## Syarat

Butuh Python dan Git.

Cek Python:

```bash
python --version
```

Cek Git:

```bash
git --version
```

Kalau dua-duanya muncul versi, lanjut.

---

## Install

Clone atau extract project ini ke folder pilihanmu.

Contoh pakai Git:

```bash
git clone https://github.com/tiomultazem/project-toolkit "D:\tools\Project Toolkit"
```

Atau download ZIP, lalu extract ke folder pilihan.

Masuk ke folder Project Toolkit.

```bash
cd "D:\tools\Project Toolkit"
```

Install editable.

```bash
python -m pip install -e .
```

Mode editable berarti cukup install sekali. Kalau kode `pt` diubah, command ikut berubah.

---

## Tes

```bash
pt
```

Kalau menu muncul, aman.

Untuk detail command:

```bash
pt 1
pt 2
pt 3
pt 4
pt 5
pt 6
pt 7
```

---

## Command

### 1. Mini

Hard minify + obfuscate file Python.

Single file:

```bash
pt mini file.py
```

Banyak file, pisahkan dengan koma tanpa spasi:

```bash
pt mini app.py,main.py,utils.py
```

Dari listfile:

```bash
pt mini list.txt
```

Satu folder:

```bash
pt mini folder/
```

Dengan passphrase:

```bash
pt mini file.py aku-cinta-kantorku
pt mini app.py,main.py aku-cinta-kantorku
pt mini list.txt aku-cinta-kantorku
pt mini folder/ aku-cinta-kantorku
```

Isi `list.txt` boleh dipisah enter:

```txt
app.py
main.py
utils.py
```

Atau koma:

```txt
app.py,main.py,utils.py
```

Behavior output:

```txt
file.py -> realfile.py sebagai file asli
file.py -> jadi file obfuscated dengan nama lama

folder/ -> realfolder/ sebagai folder asli
folder/ -> jadi folder obfuscated dengan nama lama
```

Penting:

- `app.py,main.py` benar
- `app.py, main.py` salah
- spasi setelah daftar file/folder dianggap passphrase
- passphrase bebas/custom, tapi tidak boleh pakai spasi
- passphrase berlaku untuk semua file/folder dalam command
- tanpa passphrase tidak bisa dibalik pakai `pt demini`

### 2. Demini

Balikin hasil `pt mini` yang pakai passphrase.

Single file:

```bash
pt demini file.py passphrase
```

Banyak file:

```bash
pt demini app.py,main.py passphrase
```

Dari listfile:

```bash
pt demini list.txt passphrase
```

Satu folder:

```bash
pt demini folder/ passphrase
```

Behavior output:

```txt
file.py -> realfile.py
folder/ -> realfolder/realfile.py
```

Catatan:

- input harus hasil `pt mini ... passphrase`
- passphrase harus sama dengan saat `pt mini`
- listfile boleh dipisah enter atau koma
- file/folder yang gagal akan dilewati, proses lain tetap lanjut

### 3. Enkrip

Enkripsi file/folder dari folder sekarang ke `extras.ptk`.

Cara manual:

```bash
pt enkrip passphrase
```

Setelah enter, isi daftar file/folder dipisah koma.

```txt
.env,app.py,static/
```

Cara listfile:

```bash
pt enkrip passphrase listfile.txt
```

Isi `listfile.txt` boleh dipisah enter:

```txt
.env
app.py
static/
```

Atau koma:

```txt
.env,app.py,static/
```

Output:

```txt
extras.ptk
```

Catatan:

- passphrase bebas/custom, tapi tidak boleh pakai spasi
- file apa saja bisa: `.env`, `.jpg`, `.png`, `.xlsx`, dll
- folder boleh ditulis `static/` biar jelas
### 4. Dekrip

Dekripsi `extras.ptk` ke folder sekarang.

```bash
pt dekrip passphrase
```

Contoh:

```bash
pt dekrip aku-cinta-kantorku
```

Syarat:

- `extras.ptk` ada di folder sekarang
- passphrase sama seperti saat `pt enkrip`

### 5. Commit

Jalankan `git add .`, `git commit -m`, lalu `git push origin main` dari folder sekarang.

```bash
pt commit pesan commit
```

Contoh:

```bash
pt commit update readme
```

Yang dijalankan:

```bash
git add .
git commit -m "update readme"
git push origin main
```

Catatan:

- semua kata setelah `commit` jadi pesan commit
- branch push masih tetap `main`
- kalau branch lokal masih `master`, tool akan coba ubah ke `main` saat push perlu
- kalau remote belum ada, tool akan tanya untuk add remote

### 6. Versi

Tulis versi project ke `config.json` di folder sekarang.

```bash
pt versi x
```

Atau pakai suffix:

```bash
pt versi x suffix
```

Format versi:

```txt
x.YY.MMDD
x.YY.MMDD.suffix
```

Contoh tanggal 22 Mei 2026:

```bash
pt versi 1
```

Hasil di `config.json`:

```json
{
  "version": "1.26.0522"
}
```

Contoh dengan suffix:

```bash
pt versi 1 beta
```

Hasil:

```json
{
  "version": "1.26.0522.beta"
}
```

Aturan:

- `x` wajib angka
- `suffix` opsional
- `suffix` tidak boleh pakai spasi
- kalau `config.json` belum ada, file dibuat otomatis
- kalau `changelog.json` belum ada, file dibuat otomatis
- setiap bikin versi baru, user diminta menulis changelog
- changelog ditulis ke `changelog.json`
- enter kosong menyelesaikan input changelog
- versi angka sama tapi suffix beda dianggap versi baru
- versi angka dan suffix sama akan gagal


### 7. Updater

Inject updater otomatis ke project Flask atau CTk.

Format command:

```bash
pt updater flask main.py templates/index.html
pt updater ctk main.py
```

Behavior Flask:

- membuat `pt_update_core.py`
- inject route backend ke `main.py`
- inject SweetAlert ke `templates/index.html`
- user tetap buka halaman home biasa
- JavaScript otomatis cek `/pt-updater/check`
- kalau ada versi baru, SweetAlert muncul
- klik unduh pembaruan akan hit `/pt-updater/apply`
- backend download zip repo, unpack, replace isi project, hapus temp, lalu rerun app

Behavior CTk/Desktop:

- membuat `updater.py`
- inject pemanggil updater ke `main.py`
- saat app jalan, `updater.py` dibuka sebagai proses kecil terpisah
- kalau ada versi baru, muncul jendela updater CTk
- klik unduh pembaruan akan download zip repo, unpack, replace isi project, hapus temp, lalu rerun app

Syarat umum:

- repo GitHub public ada di remote `origin`
- branch default `main`
- repo punya `config.json`
- repo punya `changelog.json`
- project lokal punya `config.json`
- update boleh replace isi project sekarang
- file yang dilewati: `.git`, `.env`, `extras.ptk`, `.pt_backup`, `__pycache__`, `.venv`, `venv`, `env`, `node_modules`

Syarat Flask:

- `main.py` adalah file Flask utama
- `main.py` punya object `app = Flask(...)`
- `templates/index.html` adalah halaman home yang dibuka user
- app dijalankan dengan `python main.py`

Syarat CTk/Desktop:

- `main.py` adalah file utama desktop
- app dijalankan dengan `python main.py`
- project memakai `customtkinter`
- app boleh ditutup lalu dijalankan ulang oleh updater

Catatan:

- updater membuat backup ke `.pt_backup/` sebelum replace
- kalau Flask dijalankan via service, gunicorn, waitress, atau hosting khusus, restart otomatis bisa butuh mode khusus
- kalau remote private, updater belum support token
- kalau file sedang dikunci Windows, replace bisa gagal
---
## File Yang Didukung

`pt enkrip` bisa untuk file/folder apa saja.

Contoh:

- `.env`
- `.py`
- `.jpg`
- `.png`
- `.xlsx`
- `static/`
- `templates/`

---

## Struktur Project

```txt
project-toolkit/
|-- pyproject.toml
|-- README.md
|-- pt/
    |-- __init__.py
    |-- cli.py
    |-- commands.py
    |-- crypto.py
    |-- minifier.py
    |-- archive.py
    |-- gittools.py
    |-- versioning.py
    `-- paths.py
```

---

## pyproject.toml

Bagian command global ada di sini.

```toml
[project.scripts]
pt = "pt.cli:main"
```

Artinya command `pt` menjalankan fungsi `main()` di `pt/cli.py`.

---

## Troubleshooting

### `pt` tidak dikenali

Cek:

```bash
where pt
```

Kalau kosong, folder Scripts Python belum masuk PATH.

Untuk Anaconda biasanya:

```txt
C:\ProgramData\anaconda3\Scripts
```


### `python` tidak dikenali

Install Python, lalu centang:

```txt
Add python.exe to PATH
```

Kalau pakai Anaconda, buka lewat Anaconda Prompt.

---

## Uninstall

```bash
python -m pip uninstall project-toolkit
```

---

## Catatan

`pt mini` tanpa passphrase tidak punya payload reverse.

`pt mini` dengan passphrase bisa direverse karena source asli disimpan terenkripsi di dalam file obfuscated.

`pt enkrip` tidak khusus Python. Dia membungkus bytes file/folder apa saja ke `extras.ptk`.

Satu `pt`, banyak fungsi.
