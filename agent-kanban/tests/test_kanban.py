import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import build_opener, ProxyHandler, Request

CLI = Path(__file__).resolve().parents[1] / "scripts/kanban.py"
HTTP = build_opener(ProxyHandler({}))


class BoardTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = self.temp.name
        self.call("init", "--title", "Test goal")

    def tearDown(self):
        self.call("stop")
        self.temp.cleanup()

    def call(self, *args, actor="lead", success=True, env=None):
        environment = {key: value for key, value in os.environ.items() if key != "AGENT_KANBAN_HOST"}
        environment.update(env or {})
        result = subprocess.run([sys.executable, str(CLI), "--state", self.state,
                                 "--actor", actor, *args], env=environment, capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return json.loads(result.stderr)["error"]

    def add(self, id="task-01", *args):
        return self.call("add", id, "--title", "An observable outcome", *args)

    def test_persistent_review_workflow_and_history(self):
        self.add()
        self.call("claim", "task-01", actor="worker")
        self.assertIn("reviewer", self.call("move", "task-01", "--status", "in_review", success=False))
        self.call("move", "task-01", "--status", "in_review", "--reviewer", "lead", "--expected-revision", "2", actor="worker")
        self.assertIn("evidence", self.call("move", "task-01", "--status", "done", success=False))
        self.call("move", "task-01", "--status", "done", "--expected-revision", "3", "--evidence", "Lead reviewed behavior; focused check passed")
        board = self.call("list")
        self.assertEqual(board["tasks"][0]["status"], "done")
        self.assertEqual(board["tasks"][0]["assignee"], "worker")
        self.assertEqual(board["tasks"][0]["revision"], 4)
        self.assertEqual(len(board["events"]), 5)

    def test_competing_claims_have_one_winner(self):
        self.add()
        def claim(actor):
            return subprocess.run([sys.executable, str(CLI), "--state", self.state,
                                   "--actor", actor, "claim", "task-01"], capture_output=True, text=True)
        with concurrent.futures.ThreadPoolExecutor(8) as pool:
            results = list(pool.map(claim, [f"worker-{i}" for i in range(8)]))
        self.assertEqual(sum(r.returncode == 0 for r in results), 1)
        winner = json.loads(next(r.stdout for r in results if r.returncode == 0))
        self.assertEqual(self.call("show", "task-01")["assignee"], winner["assignee"])

    def test_stale_edits_do_not_erase_work(self):
        self.add()
        self.call("edit", "task-01", "--expected-revision", "1", "--description", "First edit")
        self.assertIn("Conflict", self.call("edit", "task-01", "--expected-revision", "1", "--description", "Stale overwrite", success=False))
        self.assertEqual(self.call("show", "task-01")["description"], "First edit")

    def test_dependencies_cycles_and_blockers(self):
        self.add("parent")
        self.add("child", "--depends-on", "parent")
        self.assertIn("not done", self.call("claim", "child", success=False))
        self.assertIn("cycle", self.call("edit", "parent", "--depends-on", "child", success=False))
        self.assertIn("blocker", self.call("move", "parent", "--status", "blocked", success=False))
        self.call("move", "parent", "--status", "blocked", "--blocker", "Needs input")
        self.call("claim", "parent")
        self.assertEqual(self.call("show", "parent")["blocker"], "")
        self.call("move", "parent", "--status", "done", "--evidence", "Reviewed")
        self.call("claim", "child")

    def test_independent_concurrent_notes_are_not_lost(self):
        self.add()
        def note(i):
            self.call("note", "task-01", "--note", f"Milestone {i}", actor=f"worker-{i}")
        with concurrent.futures.ThreadPoolExecutor(6) as pool:
            list(pool.map(note, range(12)))
        board = self.call("list")
        self.assertEqual(board["tasks"][0]["revision"], 13)
        self.assertEqual(len(board["events"]), 14)

    def test_http_read_only_etag_and_lifecycle(self):
        self.add()
        server = self.call("start", "--port", "0")
        self.assertEqual(server["host"], "127.0.0.1")
        self.assertEqual(self.call("start", "--port", "0")["instance"], server["instance"])
        base = server["local_url"]
        with HTTP.open(base + "/api/board") as response:
            etag = response.headers["ETag"]
            before = json.load(response)
        for path in ("/", "/app.js", "/style.css", "/health"):
            with HTTP.open(base + path) as response:
                self.assertEqual(response.status, 200)
        for path in ("/fonts/inter-latin.woff2", "/fonts/ibm-plex-mono-latin.woff2"):
            with HTTP.open(base + path) as response:
                self.assertEqual(response.headers["Content-Type"], "font/woff2")
                self.assertEqual(response.read(4), b"wOF2")
        with self.assertRaises(HTTPError) as cached:
            HTTP.open(Request(base + "/api/board", headers={"If-None-Match": etag}))
        self.assertEqual(cached.exception.code, 304)
        cached.exception.close()
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.assertRaises(HTTPError) as denied:
                HTTP.open(Request(base + "/api/board", method=method, data=b'{}'))
            self.assertEqual(denied.exception.code, 501)
            denied.exception.close()
        with self.assertRaises(HTTPError) as hidden:
            HTTP.open(base + "/../board.sqlite3")
        self.assertEqual(hidden.exception.code, 404)
        hidden.exception.close()
        self.assertEqual(before, self.call("list"))
        self.call("claim", "task-01")
        with HTTP.open(Request(base + "/api/board", headers={"If-None-Match": etag})) as response:
            self.assertNotEqual(response.headers["ETag"], etag)
            self.assertEqual(json.load(response)["tasks"][0]["status"], "in_progress")
        self.call("stop")
        self.assertFalse(self.call("status")["running"])
        restarted = self.call("start", "--port", "0")
        self.assertNotEqual(restarted["instance"], server["instance"])
        self.assertEqual(self.call("show", "task-01")["status"], "in_progress")

    def test_bind_environment_precedence_and_blank_defaults(self):
        for value, flags, expected in [
            (None, [], "127.0.0.1"),
            ("", [], "127.0.0.1"),
            ("   ", [], "127.0.0.1"),
            ("0.0.0.0", [], "0.0.0.0"),
            ("0.0.0.0", ["--host", "127.0.0.1"], "127.0.0.1"),
        ]:
            with self.subTest(value=value, flags=flags):
                environment = {} if value is None else {"AGENT_KANBAN_HOST": value}
                server = self.call("start", "--port", "0", *flags, env=environment)
                try:
                    self.assertEqual(server["host"], expected)
                    with HTTP.open(server["local_url"] + "/health") as response:
                        self.assertEqual(json.load(response)["instance"], server["instance"])
                finally:
                    self.call("stop")


if __name__ == "__main__":
    unittest.main()
