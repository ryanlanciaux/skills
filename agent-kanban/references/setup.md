# Runtime setup and recovery

Run `sh "$SKILL_DIR/scripts/kanban.sh" doctor` before initializing or serving a
board. The shell launcher works without Python and prints platform-specific setup
instructions on failure. It never installs software. All normal CLI commands can
be passed through the same launcher.

Requirements: Linux/macOS, Python 3.10+, working `sqlite3` and Unix `fcntl` modules.
SQLite is embedded in the Python process. No SQLite command-line program, database
service, pip package, npm or MCP installation is needed. The doctor opens only an
in-memory test database; it does not create or modify board state.

## Missing or old Python

- Debian/Ubuntu: `sudo apt-get update`, then `sudo apt-get install python3`.
- Fedora: `sudo dnf install python3`.
- Arch Linux: `sudo pacman -Syu python` (the normal full system upgrade avoids a partial upgrade).
- Alpine Linux: `sudo apk add python3`.
- macOS: use the current installer from [Python downloads](https://www.python.org/downloads/macos/).
- Other Linux distributions: use the distribution's supported Python package.
- Windows: native Windows is unsupported because the server uses Unix file
  locking and process signals. Use WSL/Linux and follow its distribution steps.

These are instructions to present, not commands for the launcher to execute.
Use existing task authorization for any requested setup; providing this guidance
does not require a new approval step. On older distributions the default Python
may still be too old. Select a supported newer interpreter and rerun doctor:

```sh
export AGENT_KANBAN_PYTHON="/absolute/path/to/python3"
sh "$SKILL_DIR/scripts/kanban.sh" doctor
```

The override is one executable path, not a shell command or argument list.

## Python exists but SQLite fails

Python's `sqlite3` is an [optional standard-library module](https://docs.python.org/3/library/sqlite3.html).
A minimal installation or custom Python build may omit it. Repair the matching
Python distribution package, or install its SQLite module if that distributor
packages it separately. For pyenv/source builds, install the SQLite development headers
appropriate to the OS and rebuild that interpreter, or select a complete Python
distribution. Recreating a virtual environment alone does not repair its base
interpreter. Installing the SQLite CLI or `pip install sqlite3` is not the fix.

Re-run doctor with the same interpreter that will run the board. If it still
fails, report the actual error and selected interpreter; do not loop over
installers, delete state, or claim the server started. Keep the requested work's
status honest while the viewer is unavailable.

## Runtime passes but the board does not start

Use the CLI error and the chosen state directory's `server.log`. Common causes
include a port already in use, a non-writable state directory, or an uninitialized
board. Choose a free port for another project; preserve each project's separate
state directory. Do not reinitialize or delete an existing database to repair a
startup failure. Confirm `status` and `/health` before presenting a live URL.

Package references: [Ubuntu Python setup](https://documentation.ubuntu.com/ubuntu-for-developers/howto/python-setup/),
[Fedora Python](https://developer.fedoraproject.org/tech/languages/python/python-installation.html),
[Arch Python package](https://archlinux.org/packages/core/x86_64/python/),
[Alpine Python package](https://pkgs.alpinelinux.org/package/v3.23/main/x86_64/python3).
