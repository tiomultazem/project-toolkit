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


def run_git_commit(
    project_dir: Path,
    message: str,
    remote_name: str = DEFAULT_REMOTE,
    branch: str = DEFAULT_BRANCH,
) -> bool:  # git add/commit kalau perlu, lalu push main
    if not message.strip():
        raise ValueError("pesan commit kosong")

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