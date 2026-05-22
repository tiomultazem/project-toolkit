# Project Toolkit

`pt` adalah command-line toolkit untuk bantu manage project dari direktori mana pun.

Belakangan ini aku nyadar aku nyepam file-file yang sama di setiap project. Obfuscator, minifier-deminifier, decryptor-encryptor.

Trus tiba-tiba sambil melamun aku dapet ilham: kenapa ga kujadikan satu tools aja yang ga perlu ku-push ke setiap repo?

Lalu dibuatlah project ini.

---


## Isi sekarang

- `mini`: minify + obfuscate file Python
- `demini`: balikin hasil `mini` yang pakai passphrase
- `enkrip`: enkripsi kumpulan file/folder ke `extras.mwehe`
- `dekrip`: dekripsi `extras.mwehe` ke folder sekarang
- `commit`: git add, commit, lalu push ke `origin main`
- `versi`: tulis versi project ke `config.json` dan changelog ke `changelog.json`

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
```

---

## Command

### 1. Mini

Minify + obfuscate file Python.

```bash
pt mini file.py
```

Output dibuat di folder yang sama.

```txt
filemob.py
```

Contoh:

```bash
pt mini app.py
```

Hasil:

```txt
appmob.py
```

### 2. Mini Dengan Passphrase

Sama seperti `mini`, tapi bisa dibalik lagi.

```bash
pt mini file.py passphrase
```

Contoh:

```bash
pt mini app.py aku-cinta-kantorku
```

Output:

```txt
appmob.py
```

Catatan:

- passphrase bebas/custom
- passphrase tidak boleh pakai spasi
- file hasil ini bisa dibalik pakai `pt demini`

### 3. Demini

Balikin hasil `pt mini file.py passphrase`.

```bash
pt demini filemob.py passphrase
```

Contoh:

```bash
pt demini appmob.py aku-cinta-kantorku
```

Output:

```txt
demappmob.py
```

Catatan: `demini` tidak bisa membalik file hasil `mini` tanpa passphrase.

### 4. Enkrip Manual

Enkripsi file/folder dari folder sekarang ke `extras.mwehe`.

```bash
pt enkrip passphrase
```

Setelah enter, isi daftar file/folder dipisah koma.

```txt
.env,app.py,static/
```

Output:

```txt
extras.mwehe
```

### 5. Enkrip Dari Listfile

Enkripsi file/folder dari daftar di file teks.

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

Output tetap:

```txt
extras.mwehe
```

### 6. Dekrip

Dekripsi `extras.mwehe` ke folder sekarang.

```bash
pt dekrip passphrase
```

Contoh:

```bash
pt dekrip aku-cinta-kantorku
```

Syarat:

- `extras.mwehe` ada di folder sekarang
- passphrase sama seperti saat `pt enkrip`

### 7. Commit

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

### 8. Versi

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

`pt mini` tanpa passphrase tidak bisa direverse.

`pt mini` dengan passphrase bisa direverse karena source asli disimpan terenkripsi di dalam `filemob.py`.

`pt enkrip` tidak khusus Python. Dia membungkus bytes file/folder apa saja ke `extras.mwehe`.

Satu `pt`, banyak fungsi.
