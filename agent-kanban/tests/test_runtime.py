import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


class RuntimeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="kanban runtime ")
        self.root = Path(self.temp.name)
        self.state = self.root / "board state"
        self.env = {key: value for key, value in os.environ.items()
                    if key not in ("AGENT_KANBAN_PYTHON", "PYTHONPATH", "PYTHONHOME")}
        self.env.update(AGENT_KANBAN_STATE=str(self.state), AGENT_KANBAN_ACTOR="test")

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, direct=False, scripts=SCRIPTS):
        command = [sys.executable, str(scripts / "kanban.py")] if direct else ["/bin/sh", str(scripts / "kanban.sh")]
        return subprocess.run(command + list(args), env=self.env, capture_output=True, text=True, timeout=10)

    def test_doctor_needs_no_sqlite_executable_or_state(self):
        self.env.update(PATH="", AGENT_KANBAN_PYTHON=sys.executable)
        result = self.run_cli("doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("runtime ready", result.stdout)
        self.assertFalse(self.state.exists())

    def test_launcher_forwards_arguments_and_paths_with_spaces(self):
        scripts = self.root / "skill copy" / "scripts"
        shutil.copytree(SCRIPTS, scripts, ignore=shutil.ignore_patterns("__pycache__"))
        interpreter = self.root / "chosen python"
        interpreter.symlink_to(sys.executable)
        self.env["AGENT_KANBAN_PYTHON"] = str(interpreter)
        title = "Board with spaces; $(not-a-command)"
        result = self.run_cli("init", "--title", title, scripts=scripts)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli("list", scripts=scripts)
        self.assertEqual(json.loads(result.stdout)["board"]["title"], title)

    def test_no_python_gives_os_instructions_without_running_installers(self):
        bins = self.root / "bin"
        bins.mkdir()
        marker = self.root / "installer-was-run"
        self.env["PATH"] = str(bins)
        for operating_system, manager, expected in [
            ("Linux", "apt-get", "apt-get install python3"),
            ("Linux", "dnf", "dnf install python3"),
            ("Linux", "pacman", "pacman -Syu python"),
            ("Linux", "apk", "apk add python3"),
            ("Darwin", None, "python.org/downloads/macos/"),
            ("Unknown", None, "WSL/Linux"),
        ]:
            with self.subTest(os=operating_system, manager=manager):
                for path in bins.iterdir():
                    path.unlink()
                uname = bins / "uname"
                uname.write_text("#!/bin/sh\nprintf '%s\\n' " + operating_system + "\n")
                uname.chmod(0o755)
                if manager:
                    installer = bins / manager
                    installer.write_text("#!/bin/sh\nprintf invoked > '" + str(marker) + "'\n")
                    installer.chmod(0o755)
                result = self.run_cli("init", "--title", "Must not create")
                self.assertEqual(result.returncode, 2)
                self.assertIn("no Python interpreter", result.stderr)
                self.assertIn(expected, result.stderr)
                self.assertIn("doctor", result.stderr)
                self.assertFalse(self.state.exists())
                self.assertFalse(marker.exists())

    def test_missing_override_does_not_silently_choose_another_python(self):
        self.env["AGENT_KANBAN_PYTHON"] = str(self.root / "missing python")
        result = self.run_cli("doctor")
        self.assertEqual(result.returncode, 2)
        self.assertIn("selected Python executable was not found", result.stderr)
        self.assertFalse(self.state.exists())

    def test_invalid_runtimes_fail_before_mutation_for_both_entrypoints(self):
        hooks = self.root / "hooks"
        hooks.mkdir()
        self.env.update(PYTHONPATH=str(hooks), AGENT_KANBAN_PYTHON=sys.executable)
        cases = [
            ("sys.version_info = (3, 9, 0, 'final', 0)", "Python 3.10+"),
            ("sys.modules['sqlite3'] = None", "SQLite support is missing or unusable"),
            ("import types\nsys.modules['sqlite3'] = types.SimpleNamespace(connect=lambda _: (_ for _ in ()).throw(OSError('broken library')))", "broken library"),
            ("sys.modules['fcntl'] = None", "file-locking module"),
            ("sys.platform = 'win32'", "WSL/Linux"),
        ]
        for mutation, expected in cases:
            for direct in (False, True):
                with self.subTest(mutation=mutation, direct=direct):
                    (hooks / "sitecustomize.py").write_text("import sys\n" + mutation + "\n")
                    shutil.rmtree(hooks / "__pycache__", ignore_errors=True)
                    result = self.run_cli("init", "--title", "Must not create", direct=direct)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn(expected, result.stderr)
                    self.assertIn("setup.md", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertFalse(self.state.exists())


if __name__ == "__main__":
    unittest.main()
