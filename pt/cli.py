import sys

from .commands import (
    commit_command,
    demini_command,
    dekrip_command,
    detail_help,
    enkrip_command,
    mini_command,
    show_help,
    updater_command,
    versi_command,
)


def main() -> int:  # router command utama CLI
    args = sys.argv[1:]
    command = args[0] if args else ""

    try:
        if command == "mini":
            return mini_command(args)
        if command == "demini":
            return demini_command(args)
        if command == "enkrip":
            return enkrip_command(args)
        if command == "dekrip":
            return dekrip_command(args)
        if command == "commit":
            return commit_command(args)
        if command == "versi":
            return versi_command(args)
        if command == "updater":
            return updater_command(args)
        if command in {"1", "2", "3", "4", "5", "6", "7"}:
            return detail_help(command)
        return show_help()
    except Exception as error:
        print(f"gagal: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())