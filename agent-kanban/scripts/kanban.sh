#!/bin/sh
# This entrypoint can explain setup even when Python is absent. It installs nothing.
case "$0" in */*) kanban_parent=${0%/*} ;; *) kanban_parent=. ;; esac
kanban_scripts=$(CDPATH= cd -- "$kanban_parent" && pwd) || exit 2

setup_help() {
    printf '\n%s\n' 'Agent Kanban needs Python 3.10+ with its sqlite3 module on Linux/macOS.' >&2
    kanban_os=$(uname -s 2>/dev/null || printf unknown)
    case "$kanban_os" in
        Darwin)
            printf '%s\n' 'macOS: install current Python 3 from https://www.python.org/downloads/macos/.' >&2
            ;;
        Linux)
            if command -v apt-get >/dev/null 2>&1; then
                printf '%s\n' 'Debian/Ubuntu: sudo apt-get update' 'Then: sudo apt-get install python3' >&2
            elif command -v dnf >/dev/null 2>&1; then
                printf '%s\n' 'Fedora: sudo dnf install python3' >&2
            elif command -v pacman >/dev/null 2>&1; then
                printf '%s\n' 'Arch Linux: sudo pacman -Syu python' >&2
            elif command -v apk >/dev/null 2>&1; then
                printf '%s\n' 'Alpine Linux: sudo apk add python3' >&2
            else
                printf '%s\n' 'Linux: install Python 3.10+ and its SQLite module using your distribution package manager.' >&2
            fi
            ;;
        *) printf '%s\n' 'Use Linux/macOS (Windows: use WSL/Linux), then install Python 3.10+ with SQLite support.' >&2 ;;
    esac
    printf '%s\n' \
        'If your distribution only provides older Python, use a supported newer runtime.' \
        'If Python already exists but SQLite is missing, repair its distribution package or rebuild that interpreter with SQLite support.' \
        'Installing the sqlite3 command-line tool or running pip install sqlite3 does not repair Python SQLite support.' \
        'To select another interpreter, set AGENT_KANBAN_PYTHON to its executable path (no arguments).' >&2
    printf 'After setup, rerun: sh "%s/kanban.sh" doctor\n' "$kanban_scripts" >&2
    printf 'More help: %s/../references/setup.md\n' "$kanban_scripts" >&2
}

if [ -n "${AGENT_KANBAN_PYTHON:-}" ]; then
    kanban_python=$AGENT_KANBAN_PYTHON
elif command -v python3 >/dev/null 2>&1; then
    kanban_python=python3
elif command -v python >/dev/null 2>&1; then
    kanban_python=python
else
    printf '%s\n' 'Agent Kanban: no Python interpreter was found on PATH.' >&2
    setup_help
    exit 2
fi
if ! command -v "$kanban_python" >/dev/null 2>&1; then
    printf 'Agent Kanban: selected Python executable was not found: %s\n' "$kanban_python" >&2
    setup_help
    exit 2
fi
if ! "$kanban_python" "$kanban_scripts/check_runtime.py" >/dev/null; then
    setup_help
    exit 2
fi
if [ "$#" -eq 1 ] && [ "$1" = doctor ]; then
    exec "$kanban_python" "$kanban_scripts/check_runtime.py"
fi
exec "$kanban_python" "$kanban_scripts/kanban.py" "$@"
