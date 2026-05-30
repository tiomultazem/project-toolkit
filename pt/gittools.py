import subprocess
from pathlib import Path


DEFAULT_BRANCH = "main"
DEFAULT_REMOTE = "origin"


class GitCommandError(RuntimeError):  # error git dengan output asli
    def __init__(self, args: list[str], output: str):
        self.args = args
        self.output = output.strip()
        super().__init__("command gagal: git " + " ".join(args))


def git_result(project_dir: Path, args: list[str]) -> subprocess.CompletedProcess[str]:  # run git mentah
    return subprocess.run(
        ["git", *args],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )


def run_git(project_dir: Path, args: list[str]) -> str:  # jalankan git dan stop kalau gagal
    result = git_result(project_dir, args)
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        raise GitCommandError(args, output)
    if output.strip():
        print(output.strip())
    return output


def status_lines(project_dir: Path) -> list[str]:  # baca status porcelain tanpa print
    result = git_result(project_dir, ["status", "--porcelain"])
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        raise GitCommandError(["status", "--porcelain"], output)
    return [line for line in result.stdout.splitlines() if line.strip()]


def has_unstaged_or_untracked(lines: list[str]) -> bool:  # cek perlu git add atau tidak
    for line in lines:
        if line.startswith("??"):
            return True
        if len(line) > 1 and line[1] != " ":
            return True
    return False


def has_staged_changes(project_dir: Path) -> bool:  # cek ada staged changes siap commit
    result = git_result(project_dir, ["diff", "--cached", "--quiet"])
    if result.returncode == 0:
        return False
    if result.returncode == 1:
        return True
    output = (result.stdout or "") + (result.stderr or "")
    raise GitCommandError(["diff", "--cached", "--quiet"], output)


def remote_exists(project_dir: Path, remote_name: str = DEFAULT_REMOTE) -> bool:  # cek remote ada
    result = subprocess.run(
        ["git", "remote", "get-url", remote_name],
        cwd=project_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return result.returncode == 0


def ask_yes_no(question: str) -> bool:  # tanya y/n sederhana
    answer = input(question).strip().lower()
    return answer in {"y", "yes"}


def ask_default(question: str, default: str) -> str:  # input dengan default
    answer = input(f"{question} [{default}]: ").strip()
    return answer or default


def add_remote_flow(project_dir: Path) -> tuple[bool, str, str]:  # tambah remote interaktif
    print("remote belum ada")
    if not ask_yes_no("add remote? y/n: "):
        return False, DEFAULT_REMOTE, DEFAULT_BRANCH

    remote_name = ask_default("nama remote", DEFAULT_REMOTE)
    remote_url = input("remote url: ").strip()
    if not remote_url:
        raise ValueError("remote url kosong")
    branch = ask_default("branch", DEFAULT_BRANCH)

    run_git(project_dir, ["remote", "add", remote_name, remote_url])
    print(f"remote ditambah: {remote_name} -> {remote_url}")
    return True, remote_name, branch


def is_missing_branch_error(error: GitCommandError, branch: str) -> bool:  # deteksi push branch belum ada
    output = error.output.lower()
    return (
        "src refspec" in output
        and branch.lower() in output
        and "does not match any" in output
    )


def push_with_branch_fix(project_dir: Path, remote_name: str, branch: str) -> None:  # push, fix branch kalau perlu
    try:
        run_git(project_dir, ["push", remote_name, branch])
    except GitCommandError as error:
        if not is_missing_branch_error(error, branch):
            raise
        print(f"branch {branch} belum ada. ubah branch lokal ke {branch} dulu")
        run_git(project_dir, ["branch", "-M", branch])
        run_git(project_dir, ["push", "-u", remote_name, branch])


def stage_and_commit_if_needed(project_dir: Path, message: str) -> None:  # add/commit sesuai kondisi repo
    lines = status_lines(project_dir)
    if has_unstaged_or_untracked(lines):
        run_git(project_dir, ["add", "."])
    elif lines:
        print("perubahan sudah staged, skip git add")
    else:
        print("tidak ada perubahan baru, lanjut push")

    if has_staged_changes(project_dir):
        run_git(project_dir, ["commit", "-m", message])
    else:
        print("tidak ada staged changes, skip commit")


def _relative_git_path(project_dir: Path, file_path: str) -> str:  # path aman untuk git pathspec
    resolved = (project_dir / file_path).resolve()
    try:
        relative = resolved.relative_to(project_dir.resolve())
    except ValueError as error:
        raise ValueError("file harus berada di dalam project") from error
    return relative.as_posix()


def has_file_changes(project_dir: Path, git_path: str) -> bool:  # cek satu file berubah atau untracked
    result = git_result(project_dir, ["status", "--porcelain", "--", git_path])
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        raise GitCommandError(["status", "--porcelain", "--", git_path], output)
    return bool(result.stdout.strip())


def stage_and_commit_one_if_needed(project_dir: Path, file_path: str, message: str) -> None:  # commit satu file saja
    git_path = _relative_git_path(project_dir, file_path)
    if not has_file_changes(project_dir, git_path):
        print(f"tidak ada perubahan di {git_path}, lanjut push")
        return

    run_git(project_dir, ["add", "--", git_path])
    run_git(project_dir, ["commit", "-m", message, "--", git_path])


def is_project_toolkit(project_dir: Path) -> bool:  # cek apakah project ini toolkit sendiri
    try:
        toolkit_dir = Path(__file__).parent.parent.resolve()
        return project_dir.resolve() == toolkit_dir
    except Exception:
        return False


def _is_unobfuscated_py(file_path: Path) -> bool:  # cek apakah file python tidak terobfuscate
    if not file_path.is_file():
        return False
    if file_path.suffix.lower() != ".py":
        return False
    parts = file_path.parts
    if ".pt_real" in parts or "__pycache__" in parts:
        return False
    if any(p in {".venv", "venv", "env"} for p in parts):
        return False
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    if not content.strip():
        return False
    rev_marker = "# PT_REV:"
    looks_minified = rev_marker in content or ("gettrace" in content and "marshal" in content and "_k=" in content)
    return not looks_minified


def get_files_to_check(project_dir: Path) -> list[Path]:  # ambil file-file dari git status untuk dicek
    files = []
    try:
        lines = status_lines(project_dir)
    except Exception:
        return []
    for line in lines:
        if len(line) < 4:
            continue
        if " -> " in line:
            parts = line.split(" -> ")
            path_str = parts[-1].strip().strip('"').strip("'")
        else:
            path_str = line[3:].strip().strip('"').strip("'")
        files.append((project_dir / path_str).resolve())
    return files


def run_git_commit(
    project_dir: Path,
    message: str,
    remote_name: str = DEFAULT_REMOTE,
    branch: str = DEFAULT_BRANCH,
) -> bool:  # git add/commit kalau perlu, lalu push main
    print("[DEBUG] Menjalankan run_git_commit dari Project Toolkit lokal")
    if not message.strip():
        raise ValueError("pesan commit kosong")

    if not is_project_toolkit(project_dir):
        has_unobfuscated = False
        for file_path in get_files_to_check(project_dir):
            if _is_unobfuscated_py(file_path):
                has_unobfuscated = True
                break
        if has_unobfuscated:
            if not ask_yes_no("anda akan push kode yang tidak terobfuscate. apakah anda yakin? (y/n): "):
                return False

    if not remote_exists(project_dir, remote_name):
        added, remote_name, branch = add_remote_flow(project_dir)
        if not added:
            return False
        if ask_yes_no("ulangi commit? y/n: "):
            return run_git_commit(project_dir, message, remote_name, branch)
        return False

    stage_and_commit_if_needed(project_dir, message)
    push_with_branch_fix(project_dir, remote_name, branch)
    return True

def run_git_commit_one(
    project_dir: Path,
    file_path: str,
    message: str,
    remote_name: str = DEFAULT_REMOTE,
    branch: str = DEFAULT_BRANCH,
) -> bool:  # git add/commit satu file saja, lalu push main
    print("[DEBUG] Menjalankan run_git_commit_one dari Project Toolkit lokal")
    if not file_path.strip():
        raise ValueError("file kosong")
    if not message.strip():
        raise ValueError("pesan commit kosong")

    if not is_project_toolkit(project_dir):
        resolved_file = (project_dir / file_path).resolve()
        if _is_unobfuscated_py(resolved_file):
            if not ask_yes_no("anda akan push kode yang tidak terobfuscate. apakah anda yakin? (y/n): "):
                return False

    if not remote_exists(project_dir, remote_name):
        added, remote_name, branch = add_remote_flow(project_dir)
        if not added:
            return False
        if ask_yes_no("ulangi commit? y/n: "):
            return run_git_commit_one(project_dir, file_path, message, remote_name, branch)
        return False

    stage_and_commit_one_if_needed(project_dir, file_path, message)
    push_with_branch_fix(project_dir, remote_name, branch)
    return True