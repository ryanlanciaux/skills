"""Dependency preflight; keep syntax compatible with older Python for diagnostics."""
import os
import sys


def require_runtime():
    problem = None
    if sys.version_info[:2] < (3, 10):
        problem = "Python 3.10+ is required; found {}.{}.".format(*sys.version_info[:2])
    elif not sys.platform.startswith("linux") and sys.platform != "darwin":
        problem = "This skill supports Linux and macOS. On Windows, run it inside WSL/Linux."
    else:
        try:
            import fcntl
        except (ImportError, OSError) as error:
            problem = "Python's Unix file-locking module (fcntl) is unavailable: {}".format(error)
        if problem is None:
            try:
                import sqlite3
                db = sqlite3.connect(":memory:")
                try:
                    db.execute("CREATE TABLE check_runtime (value INTEGER)")
                    db.execute("INSERT INTO check_runtime VALUES (1)")
                    if db.execute("SELECT value FROM check_runtime").fetchone() != (1,):
                        raise RuntimeError("SQLite read/write check failed")
                finally:
                    db.close()
            except Exception as error:
                problem = "Python's SQLite support is missing or unusable: {}".format(error)
    if problem:
        directory = os.path.dirname(os.path.abspath(__file__))
        sys.stderr.write("Agent Kanban: {}\n".format(problem))
        sys.stderr.write("Use the kanban.sh launcher for setup instructions, or read {}.\n".format(
            os.path.join(directory, "..", "references", "setup.md")))
        raise SystemExit(2)


if __name__ == "__main__":
    require_runtime()
    sys.stdout.write("Agent Kanban runtime ready: Python {}.{}.{} with working SQLite.\n".format(*sys.version_info[:3]))
