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

Dengan passphrase opsional:

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
Tanpa passphrase:
file.py -> tetap file.py, tapi isinya obfuscated
file.py asli -> disimpan ke .pt_real/file.py

Dengan passphrase:
file.py -> tetap file.py, tapi isinya obfuscated + payload terenkripsi
file.py asli -> tidak disimpan ke .pt_real, recovery pakai pt demini

Folder:
folder/app.py -> tetap folder/app.py, tapi isinya obfuscated
folder/app.py asli -> disimpan ke .pt_real/folder/app.py hanya kalau tanpa passphrase
```

Penting:

- `.pt_real/` wajib masuk `.gitignore`
- `.pt_real/` hanya dibuat saat `pt mini` tanpa passphrase
- struktur folder asli dimirror di `.pt_real/` untuk mode tanpa passphrase
- `app.py,main.py` benar
- `app.py, main.py` salah
- spasi setelah daftar file/folder dianggap passphrase
- passphrase bebas/custom, tapi tidak wajib
- passphrase membuat recovery lewat `pt demini`, jadi `.pt_real/` tidak dibuat
- kalau file terlihat sudah minified, command akan warning `sudah berupa minified. tetap lanjutkan?`

### 2. Demini

Decrypt file hasil `pt mini ... passphrase`.

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
payload terenkripsi + passphrase -> file.py source asli
payload terenkripsi + passphrase -> folder/app.py source asli
```

Catatan:

- passphrase wajib dan harus sama dengan saat `pt mini`
- `demini` membaca payload terenkripsi dari file obfuscated
- file obfuscated tidak disimpan karena bisa dibuat ulang dengan `pt mini`
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

Jalankan git add, commit, lalu push ke `origin main` dari folder sekarang.

Commit semua perubahan:

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

Commit satu file saja:

```bash
pt commit -one file.ext pesan commit
```

Contoh:

```bash
pt commit -one file.ext commit file.ext
```

Yang dijalankan:

```bash
git add -- file.ext
git commit -m "commit file.ext" -- file.ext
git push origin main
```

Catatan:

- semua kata setelah `commit` jadi pesan commit
- untuk `-one`, semua kata setelah nama file jadi pesan commit
- `-one` hanya commit file yang disebut
- branch push masih tetap `main`
- kalau branch lokal masih `master`, tool akan coba ubah ke `main` saat push perlu
- kalau remote belum ada, tool akan tanya untuk add remote
### 6. Versi

Tulis versi project ke `config.json` di folder sekarang.

Versi pertama, saat `config.json` belum punya key versi:

```bash
pt versi x
pt versi x suffix
```

Setelah `config.json` sudah punya key versi, angka utama diambil otomatis dari config:

```bash
pt versi
pt versi suffix
```

Format versi:

```txt
x.YYMM.DD
x.YYMM.DD.suffix
```

Format lain yang juga auto-detect:

```txt
x.YY.MMDD
x.YY.MMDD.suffix
x.YY.MM.DD
x.YY.MM.DD.suffix
```

Kalau `config.json` sudah punya versi lama format `x.YY.MMDD` atau `x.YY.MM.DD`, tool akan ikut format lama itu.
Kalau format tidak terdeteksi atau versi belum ada, fallback ke `x.YYMM.DD`.

Contoh versi pertama tanggal 22 Mei 2026:

```bash
pt versi 1
```

Hasil di `config.json`:

```json
{
  "version": "1.2605.22"
}
```

Contoh versi berikutnya dengan suffix:

```bash
pt versi beta
```

Hasil:

```json
{
  "version": "1.2605.22.beta"
}
```

Invalid kalau `config.json` sudah punya `version`:

```bash
pt versi 1 beta
```

Aturan:

- `x` wajib hanya untuk versi pertama
- key versi auto detect: `version`, `Version`, `v`, `ver`, `currentVersion`, `current_version`, `appVersion`, `projectVersion`, dan variasi umum lain
- kalau key versi sudah ada, key itu dipakai lagi
- kalau belum ada key versi, tool membuat key `version`
- kalau `config.json` sudah punya key versi, angka utama `x` diambil otomatis dari config
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

`pt mini` mengubah file normal menjadi obfuscated dengan nama tetap sama; tanpa passphrase source asli disimpan ke `.pt_real/`, sedangkan dengan passphrase source asli tidak disimpan ke `.pt_real/` karena recovery dilakukan lewat `pt demini`.

`pt demini` membaca payload terenkripsi dari file obfuscated, mendekripsinya dengan passphrase, lalu menulis source asli ke path normal; file obfuscated bisa dibuat ulang kapan saja dengan `pt mini`.

`pt enkrip` tidak khusus Python. Dia membungkus bytes file/folder apa saja ke `extras.ptk`.

Satu `pt`, banyak fungsi.
