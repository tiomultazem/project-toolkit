import re
from pathlib import Path


FLASK_ROUTE_MARKER_START = "# PT_UPDATER_FLASK_START"
FLASK_ROUTE_MARKER_END = "# PT_UPDATER_FLASK_END"
FLASK_HTML_MARKER_START = "<!-- PT_UPDATER_FLASK_START -->"
FLASK_HTML_MARKER_END = "<!-- PT_UPDATER_FLASK_END -->"
CTK_MARKER_START = "# PT_UPDATER_CTK_START"
CTK_MARKER_END = "# PT_UPDATER_CTK_END"


def updater_command(args: list[str]) -> int:  # handle command pt updater
    if len(args) < 3:
        print("pakai: pt updater flask main.py templates/index.html")
        print("atau : pt updater ctk main.py")
        return 1

    mode = args[1].lower()
    base_dir = Path.cwd()
    if mode == "flask":
        if len(args) != 4:
            print("pakai: pt updater flask main.py templates/index.html")
            return 1
        return _install_flask_updater(base_dir, args[2], args[3])
    if mode == "ctk":
        if len(args) != 3:
            print("pakai: pt updater ctk main.py")
            return 1
        return _install_ctk_updater(base_dir, args[2])

    print("mode updater harus flask atau ctk")
    return 1


def _install_flask_updater(base_dir: Path, main_arg: str, template_arg: str) -> int:
    main_path = (base_dir / main_arg).resolve()
    template_path = (base_dir / template_arg).resolve()
    _must_be_inside(base_dir, main_path)
    _must_be_inside(base_dir, template_path)
    _must_exist_file(main_path, "main flask")
    _must_exist_file(template_path, "template flask")

    app_name = _find_flask_app_name(main_path)
    core_path = base_dir / "pt_update_core.py"
    _write_text(core_path, _flask_core_template(main_path.relative_to(base_dir).as_posix()))
    _inject_flask_route(main_path, app_name)
    _inject_flask_html(template_path)

    print(f"jadi: {core_path}")
    print(f"inject: {main_path}")
    print(f"inject: {template_path}")
    return 0


def _install_ctk_updater(base_dir: Path, main_arg: str) -> int:
    main_path = (base_dir / main_arg).resolve()
    _must_be_inside(base_dir, main_path)
    _must_exist_file(main_path, "main ctk")

    updater_path = base_dir / "updater.py"
    _write_text(updater_path, _ctk_updater_template(main_path.relative_to(base_dir).as_posix()))
    _inject_ctk_main(main_path)

    print(f"jadi: {updater_path}")
    print(f"inject: {main_path}")
    return 0


def _must_exist_file(path: Path, label: str) -> None:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"{label} tidak ada: {path}")


def _must_be_inside(base_dir: Path, path: Path) -> None:
    path.relative_to(base_dir.resolve())


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _replace_marker(text: str, start: str, end: str, block: str) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if pattern.search(text):
        return pattern.sub(block, text)
    return text


def _find_flask_app_name(main_path: Path) -> str:
    text = _read_text(main_path)
    match = re.search(r"^\s*([A-Za-z_]\w*)\s*=\s*Flask\s*\(", text, re.MULTILINE)
    if not match:
        raise ValueError("tidak ketemu app = Flask(...) di main flask")
    return match.group(1)


def _inject_flask_route(main_path: Path, app_name: str) -> None:
    text = _read_text(main_path)
    block = (
        f"{FLASK_ROUTE_MARKER_START}\n"
        "from pt_update_core import pt_register_flask_updater\n"
        f"pt_register_flask_updater({app_name})\n"
        f"{FLASK_ROUTE_MARKER_END}"
    )
    had_marker = FLASK_ROUTE_MARKER_START in text and FLASK_ROUTE_MARKER_END in text
    replaced = _replace_marker(text, FLASK_ROUTE_MARKER_START, FLASK_ROUTE_MARKER_END, block)
    if not had_marker:
        lines = text.splitlines()
        insert_at = None
        for index, line in enumerate(lines):
            if re.search(r"\b" + re.escape(app_name) + r"\s*=\s*Flask\s*\(", line):
                insert_at = index + 1
                break
        if insert_at is None:
            raise ValueError("gagal menentukan posisi inject Flask updater")
        lines.insert(insert_at, block)
        replaced = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    _write_text(main_path, replaced)


def _inject_flask_html(template_path: Path) -> None:
    text = _read_text(template_path)
    block = _flask_html_block()
    had_marker = FLASK_HTML_MARKER_START in text and FLASK_HTML_MARKER_END in text
    replaced = _replace_marker(text, FLASK_HTML_MARKER_START, FLASK_HTML_MARKER_END, block)
    if not had_marker:
        body_match = re.search(r"</body\s*>", text, re.IGNORECASE)
        if body_match:
            replaced = text[: body_match.start()] + block + "\n" + text[body_match.start() :]
        else:
            replaced = text.rstrip() + "\n" + block + "\n"
    _write_text(template_path, replaced)


def _inject_ctk_main(main_path: Path) -> None:
    text = _read_text(main_path)
    block = _ctk_main_block()
    had_marker = CTK_MARKER_START in text and CTK_MARKER_END in text
    replaced = _replace_marker(text, CTK_MARKER_START, CTK_MARKER_END, block)
    if not had_marker:
        lines = text.splitlines()
        insert_at = 0
        if lines and lines[0].startswith("#!"):
            insert_at = 1
        if len(lines) > insert_at and "coding" in lines[insert_at]:
            insert_at += 1
        lines.insert(insert_at, block)
        replaced = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    _write_text(main_path, replaced)


def _ctk_main_block() -> str:
    return f'''{CTK_MARKER_START}
def _pt_start_updater():
    import os as _pt_os
    import subprocess as _pt_subprocess
    import sys as _pt_sys
    from pathlib import Path as _pt_Path
    _pt_root = _pt_Path(__file__).resolve().parent
    _pt_updater = _pt_root / "updater.py"
    if not _pt_updater.exists():
        return
    _pt_kwargs = {{"cwd": str(_pt_root)}}
    if _pt_os.name == "nt":
        _pt_kwargs["creationflags"] = getattr(_pt_subprocess, "CREATE_NO_WINDOW", 0)
    _pt_subprocess.Popen([
        _pt_sys.executable,
        str(_pt_updater),
        str(_pt_Path(__file__).resolve()),
        str(_pt_os.getpid()),
    ], **_pt_kwargs)
_pt_start_updater()
{CTK_MARKER_END}'''


def _flask_html_block() -> str:
    return f'''{FLASK_HTML_MARKER_START}
<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
<script>
(function () {{
  function showUpdater(data) {{
    const items = (data.changelog || []).map(function (item) {{ return "<li>" + item + "</li>"; }}).join("");
    Swal.fire({{
      title: "Terdapat versi baru " + data.latest,
      html: "<div style='text-align:left'>" +
            "<p>Versi anda sekarang <b>" + data.current + "</b>.</p>" +
            "<p>Perubahan:</p><ul>" + items + "</ul>" +
            "<p>Unduh pembaruan?</p></div>",
      icon: "info",
      showCancelButton: true,
      confirmButtonText: "Unduh pembaruan",
      cancelButtonText: "Nanti"
    }}).then(function (result) {{
      if (!result.isConfirmed) return;
      Swal.fire({{title: "Memperbarui...", text: "Aplikasi akan restart otomatis.", allowOutsideClick: false, didOpen: function () {{ Swal.showLoading(); }} }});
      fetch("/pt-updater/apply", {{method: "POST"}})
        .then(function (res) {{ return res.json(); }})
        .then(function (res) {{
          if (!res.ok) throw new Error(res.error || "update gagal");
          Swal.fire("Selesai", "Pembaruan terpasang. Aplikasi sedang restart.", "success");
        }})
        .catch(function (err) {{ Swal.fire("Gagal", err.message, "error"); }});
    }});
  }}
  fetch("/pt-updater/check")
    .then(function (res) {{ return res.json(); }})
    .then(function (data) {{ if (data.update) showUpdater(data); }})
    .catch(function () {{}});
}})();
</script>
{FLASK_HTML_MARKER_END}'''


def _shared_update_code(main_file: str) -> str:
    return f'''import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

PT_PROJECT_ROOT = Path(__file__).resolve().parent
PT_MAIN_FILE = {main_file!r}
PT_BRANCH = "main"
PT_SKIP_NAMES = {{".git", ".env", "extras.ptk", ".pt_backup", "__pycache__", ".venv", "venv", "env", "node_modules"}}


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {{}}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _urlopen_text(url: str) -> str:
    req = urllib.request.Request(url, headers={{"User-Agent": "pt-updater"}})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8")


def _urlopen_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={{"User-Agent": "pt-updater"}})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def _remote_url() -> str:
    remote = subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=PT_PROJECT_ROOT, text=True).strip()
    if remote.startswith("git@github.com:"):
        remote = "https://github.com/" + remote.removeprefix("git@github.com:")
    if remote.endswith(".git"):
        remote = remote[:-4]
    if not remote.startswith("https://github.com/"):
        raise ValueError("remote origin harus GitHub public")
    return remote.rstrip("/")


def _repo_parts() -> tuple[str, str]:
    remote = _remote_url().removeprefix("https://github.com/")
    owner, repo = remote.split("/", 1)
    return owner, repo


def _raw_url(filename: str) -> str:
    owner, repo = _repo_parts()
    return f"https://raw.githubusercontent.com/{{owner}}/{{repo}}/{{PT_BRANCH}}/{{filename}}"


def _zip_url() -> str:
    owner, repo = _repo_parts()
    return f"https://github.com/{{owner}}/{{repo}}/archive/refs/heads/{{PT_BRANCH}}.zip"


def _version_numbers(version: str) -> list[int]:
    return [int(item) for item in re.findall(r"\\d+", version or "")]


def _is_newer(remote_version: str, current_version: str) -> bool:
    if not remote_version or remote_version == current_version:
        return False
    remote_numbers = _version_numbers(remote_version)
    current_numbers = _version_numbers(current_version)
    if remote_numbers and current_numbers and remote_numbers < current_numbers:
        return False
    return True


def check_update() -> dict:
    current_config = _read_json(PT_PROJECT_ROOT / "config.json")
    current_version = str(current_config.get("version", "0"))
    remote_config = json.loads(_urlopen_text(_raw_url("config.json")))
    remote_changelog = json.loads(_urlopen_text(_raw_url("changelog.json")))
    latest_version = str(remote_config.get("version", "0"))
    changelog = remote_changelog.get(latest_version, [])
    if isinstance(changelog, str):
        changelog = [changelog]
    return {{
        "ok": True,
        "update": _is_newer(latest_version, current_version),
        "current": current_version,
        "latest": latest_version,
        "changelog": changelog,
    }}


def _should_skip(path: Path) -> bool:
    return bool(path.parts) and path.parts[0] in PT_SKIP_NAMES


def _copy_existing_to_backup(destination: Path, backup_root: Path, relative_path: Path) -> None:
    if not destination.exists():
        return
    backup_destination = backup_root / relative_path
    backup_destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_dir():
        shutil.copytree(destination, backup_destination, dirs_exist_ok=True)
    else:
        shutil.copy2(destination, backup_destination)


def _replace_item(source: Path, destination: Path) -> None:
    if destination.is_dir():
        shutil.rmtree(destination)
    elif destination.exists():
        destination.unlink()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


def _apply_tree(source_root: Path) -> Path:
    backup_root = PT_PROJECT_ROOT / ".pt_backup" / datetime.now().strftime("%Y%m%d%H%M%S")
    backup_root.mkdir(parents=True, exist_ok=True)
    for source in source_root.iterdir():
        relative_path = Path(source.name)
        if _should_skip(relative_path):
            continue
        destination = PT_PROJECT_ROOT / relative_path
        _copy_existing_to_backup(destination, backup_root, relative_path)
        _replace_item(source, destination)
    return backup_root


def apply_update() -> dict:
    temp_dir = Path(tempfile.mkdtemp(prefix="pt_update_"))
    try:
        zip_path = temp_dir / "update.zip"
        zip_path.write_bytes(_urlopen_bytes(_zip_url()))
        extract_dir = temp_dir / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)
        roots = [path for path in extract_dir.iterdir() if path.is_dir()]
        source_root = roots[0] if len(roots) == 1 else extract_dir
        backup_root = _apply_tree(source_root)
        return {{"ok": True, "backup": str(backup_root)}}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def rerun_app(main_file: str | None = None) -> None:
    target = Path(main_file or PT_MAIN_FILE)
    if not target.is_absolute():
        target = PT_PROJECT_ROOT / target
    os.execv(sys.executable, [sys.executable, str(target)])
'''


def _flask_core_template(main_file: str) -> str:
    shared = _shared_update_code(main_file)
    return shared + '''


def pt_register_flask_updater(app):
    from flask import jsonify
    import threading

    @app.get("/pt-updater/check")
    def pt_updater_check():
        try:
            return jsonify(check_update())
        except Exception as error:
            return jsonify({"ok": False, "update": False, "error": str(error)})

    @app.post("/pt-updater/apply")
    def pt_updater_apply():
        try:
            result = apply_update()
            if result.get("ok"):
                threading.Thread(target=_pt_restart_later, daemon=True).start()
            return jsonify(result)
        except Exception as error:
            return jsonify({"ok": False, "error": str(error)}), 500


def _pt_restart_later():
    time.sleep(1.5)
    rerun_app(PT_MAIN_FILE)
'''


def _ctk_updater_template(main_file: str) -> str:
    shared = _shared_update_code(main_file)
    return shared + '''


def _kill_parent(parent_pid: int | None) -> None:
    if not parent_pid or parent_pid == os.getpid():
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(parent_pid), "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.kill(parent_pid, 15)
    except Exception:
        pass
    time.sleep(1)


def _rerun_desktop(main_file: str) -> None:
    target = Path(main_file)
    if not target.is_absolute():
        target = PT_PROJECT_ROOT / target
    subprocess.Popen([sys.executable, str(target)], cwd=str(PT_PROJECT_ROOT))


def main() -> int:
    try:
        import customtkinter as ctk
    except Exception:
        return 1

    main_file = sys.argv[1] if len(sys.argv) > 1 else PT_MAIN_FILE
    parent_pid = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else None

    try:
        data = check_update()
    except Exception:
        return 0
    if not data.get("update"):
        return 0

    app = ctk.CTk()
    app.title("PT Updater")
    app.geometry("520x360")
    app.resizable(False, False)

    title = ctk.CTkLabel(app, text=f"Terdapat versi baru {data.get('latest')}", font=("Arial", 18, "bold"))
    title.pack(padx=20, pady=(22, 8), anchor="w")

    current = ctk.CTkLabel(app, text=f"Versi anda sekarang {data.get('current')}")
    current.pack(padx=20, pady=(0, 8), anchor="w")

    changes = "\\n".join(f"- {item}" for item in data.get("changelog", [])) or "- Tidak ada changelog."
    textbox = ctk.CTkTextbox(app, width=480, height=155)
    textbox.pack(padx=20, pady=8)
    textbox.insert("1.0", "Perubahan:\\n" + changes)
    textbox.configure(state="disabled")

    status = ctk.CTkLabel(app, text="Unduh pembaruan?")
    status.pack(padx=20, pady=(4, 8), anchor="w")

    buttons = ctk.CTkFrame(app, fg_color="transparent")
    buttons.pack(padx=20, pady=8, fill="x")

    def set_status(message: str) -> None:
        app.after(0, lambda: status.configure(text=message))

    def apply_clicked() -> None:
        update_button.configure(state="disabled")
        close_button.configure(state="disabled")
        set_status("Mengunduh dan memasang pembaruan...")

        def worker():
            try:
                apply_update()
                set_status("Selesai. Aplikasi akan dijalankan ulang...")
                _kill_parent(parent_pid)
                _rerun_desktop(main_file)
                app.after(700, app.destroy)
            except Exception as error:
                app.after(0, lambda: update_button.configure(state="normal"))
                app.after(0, lambda: close_button.configure(state="normal"))
                set_status(f"Gagal: {error}")

        import threading
        threading.Thread(target=worker, daemon=True).start()

    update_button = ctk.CTkButton(buttons, text="Unduh pembaruan", command=apply_clicked)
    update_button.pack(side="left", padx=(0, 8))
    close_button = ctk.CTkButton(buttons, text="Nanti", command=app.destroy, fg_color="gray")
    close_button.pack(side="left")

    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
