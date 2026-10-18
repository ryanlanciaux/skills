import http.client
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler

CLI = Path(__file__).resolve().parents[1] / "scripts/kanban.py"
HTTP = build_opener(ProxyHandler({}))
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + b"\x00" * 40
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 40
GIF = b"GIF89a" + b"\x00" * 40
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 40
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
ROUTE = re.compile(r"/images/[0-9a-f]{32}\.(png|jpg|gif|webp)")
# Task fields recorded before bot identity, card progress and images existed.
PLAIN_KEYS = {"id", "title", "description", "status", "assignee", "reviewer", "priority", "depends_on",
              "criteria", "evidence", "blocker", "created_at", "updated_at", "last_actor", "revision"}


class CardExtrasTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        self.images = self.state / "images"
        self.call("init", "--title", "Example board")

    def tearDown(self):
        self.call("stop")
        self.temp.cleanup()

    def run_cli(self, *args):
        environment = {key: value for key, value in os.environ.items() if key != "AGENT_KANBAN_HOST"}
        return subprocess.run([sys.executable, str(CLI), "--state", str(self.state), "--actor", "lead", *args],
                              env=environment, capture_output=True, text=True)

    def call(self, *args, success=True):
        result = self.run_cli(*args)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return json.loads(result.stderr)["error"]

    def file(self, name, data):
        path = self.root / name
        path.write_bytes(data)
        return str(path)

    def stored(self):
        return sorted(p.name for p in self.images.iterdir()) if self.images.exists() else []

    def test_plain_cards_keep_their_fields(self):
        task = self.call("add", "task-01", "--title", "Plain outcome", "--assignee", "worker")
        self.assertEqual(set(task), PLAIN_KEYS)
        task = self.call("edit", "task-01", "--description", "Still plain")
        self.assertEqual(set(task), PLAIN_KEYS)
        self.assertEqual(set(self.call("list")["tasks"][0]), PLAIN_KEYS)
        self.assertEqual(self.stored(), [])

    def test_bot_identity_set_and_clear(self):
        avatar = self.file("avatar.png", PNG)
        task = self.call("add", "task-01", "--title", "Outcome", "--bot-name", "Helper bot", "--bot-avatar", avatar)
        self.assertEqual(task["bot_name"], "Helper bot")
        self.assertRegex(task["bot_avatar"], ROUTE)
        snapshot_task = self.call("list")["tasks"][0]
        self.assertEqual((snapshot_task["bot_name"], snapshot_task["bot_avatar"]), (task["bot_name"], task["bot_avatar"]))
        self.assertEqual(self.stored(), [task["bot_avatar"].rsplit("/", 1)[1]])
        renamed = self.call("edit", "task-01", "--bot-name", "Review bot")
        self.assertEqual((renamed["bot_name"], renamed["bot_avatar"]), ("Review bot", task["bot_avatar"]))
        self.assertIn("bot-name", self.call("edit", "task-01", "--bot-name", "  ", success=False))
        cleared = self.call("edit", "task-01", "--clear-bot")
        self.assertEqual(set(cleared), PLAIN_KEYS)
        self.assertEqual(self.stored(), [])

    def test_progress_validation_and_clearing(self):
        self.call("add", "task-01", "--title", "Outcome")
        for value, expected in (("0", 0), ("40", 40), ("100", 100)):
            self.assertEqual(self.call("edit", "task-01", "--progress", value)["progress"], {"percent": expected})
        for value in ("101", "-1", "4.5", "abc", "", "1000"):
            with self.subTest(progress=value):
                self.assertIn("--progress", self.call("edit", "task-01", "--progress", value, success=False))
        self.assertEqual(self.call("edit", "task-01", "--steps", "3/5")["progress"], {"done": 3, "total": 5})
        self.assertEqual(self.call("edit", "task-01", "--steps", "5/5")["progress"], {"done": 5, "total": 5})
        for value in ("6/5", "0/0", "3/0", "a/b", "3", "-1/5", "3/5/7"):
            with self.subTest(steps=value):
                self.assertIn("--steps", self.call("edit", "task-01", "--steps", value, success=False))
        self.assertIn("only one", self.call("edit", "task-01", "--progress", "10", "--steps", "1/2", success=False))
        self.assertEqual(self.call("show", "task-01")["progress"], {"done": 5, "total": 5})
        self.assertEqual(set(self.call("edit", "task-01", "--clear-progress")), PLAIN_KEYS)
        self.assertEqual(self.call("add", "task-02", "--title", "Outcome", "--progress", "25")["progress"], {"percent": 25})

    def test_valid_images_are_copied_under_random_private_names(self):
        sources = [self.file(name, data) for name, data in
                   (("one.png", PNG), ("two.jpeg", JPEG), ("three.gif", GIF), ("four.webp", WEBP))]
        task = self.call("add", "task-01", "--title", "Outcome", *[arg for s in sources for arg in ("--image", s)])
        self.assertEqual([route.rsplit(".", 1)[1] for route in task["images"]], ["png", "jpg", "gif", "webp"])
        self.assertEqual(len(set(task["images"])), 4)
        for route, data in zip(task["images"], (PNG, JPEG, GIF, WEBP)):
            self.assertRegex(route, ROUTE)
            stored = self.images / route.rsplit("/", 1)[1]
            self.assertEqual(stored.read_bytes(), data)
            self.assertEqual(stat.S_IMODE(stored.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.images.stat().st_mode), 0o700)
        appended = self.call("edit", "task-01", "--image", sources[0])
        self.assertEqual(len(appended["images"]), 5)
        replaced = self.call("edit", "task-01", "--clear-images", "--image", sources[1])
        self.assertEqual(len(replaced["images"]), 1)
        self.assertEqual(self.stored(), [replaced["images"][0].rsplit("/", 1)[1]])
        self.assertEqual(set(self.call("edit", "task-01", "--clear-images")), PLAIN_KEYS)
        self.assertEqual(self.stored(), [])

    def test_unsafe_images_are_rejected_without_leftovers(self):
        self.call("add", "task-01", "--title", "Outcome")
        rejected = {
            "svg": self.file("drawing.svg", SVG),
            "svg renamed": self.file("drawing.png", SVG),
            "text": self.file("notes.png", b"just some text, not an image"),
            "html": self.file("page.gif", b"<html><script>alert(1)</script></html>"),
            "oversize": self.file("huge.png", PNG + b"\x00" * (5 * 1024 * 1024)),
            "missing": str(self.root / "missing.png"),
            "directory": str(self.root),
            "http": "http://example.com/image.png",
            "https": "https://example.com/image.png",
            "data": "data:image/png;base64,iVBORw0KGgo=",
            "file url": "file:///etc/hosts",
        }
        valid = self.file("valid.png", PNG)
        for label, source in rejected.items():
            with self.subTest(label):
                self.call("edit", "task-01", "--image", valid, "--image", source, success=False)
                self.call("edit", "task-01", "--bot-avatar", source, success=False)
                self.assertEqual(self.stored(), [])
        self.assertIn("5 MB", self.call("edit", "task-01", "--image", rejected["oversize"], success=False))
        self.assertIn("SVG", self.call("edit", "task-01", "--image", rejected["svg"], success=False))
        self.assertIn("local files", self.call("edit", "task-01", "--image", rejected["https"], success=False))
        self.assertIn("at most 6", self.call("edit", "task-01", *["--image", valid] * 7, success=False))
        self.assertEqual(self.stored(), [])
        # Images that fail a later task validation are not left behind either.
        self.assertIn("Unknown task", self.call("edit", "task-99", "--image", valid, success=False))
        self.assertIn("already exists", self.call("add", "task-01", "--title", "Again", "--image", valid, success=False))
        self.assertEqual(self.stored(), [])
        self.assertEqual(set(self.call("show", "task-01")), PLAIN_KEYS)

    def raw(self, base, method, path, headers=None):
        parts = urlsplit(base)
        connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=5)
        try:
            # putrequest sends the path byte-for-byte (no client-side normalization).
            connection.putrequest(method, path, skip_accept_encoding=True)
            for key, value in (headers or {}).items():
                connection.putheader(key, value)
            connection.endheaders(b"{}" if method not in ("GET", "HEAD") else None)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_server_image_route_and_read_only_methods(self):
        task = self.call("add", "task-01", "--title", "Outcome", "--bot-name", "Helper bot",
                         "--bot-avatar", self.file("a.png", PNG), "--image", self.file("b.jpg", JPEG), "--steps", "1/3")
        server = self.call("start", "--port", "0")
        base = server["local_url"]

        for route, data, content_type in ((task["bot_avatar"], PNG, "image/png"), (task["images"][0], JPEG, "image/jpeg")):
            status, headers, body = self.raw(base, "GET", route)
            self.assertEqual((status, body, headers["Content-Type"]), (200, data, content_type))
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
            self.assertIn("img-src 'self'", headers["Content-Security-Policy"])
            self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
            status, headers, body = self.raw(base, "HEAD", route)
            self.assertEqual((status, body, headers["Content-Length"]), (200, b"", str(len(data))))

        name = task["images"][0].rsplit("/", 1)[1]
        for path in ("/images/../board.sqlite3", "/images/../state.db", "/images/%2e%2e/board.sqlite3",
                     "/images/%2E%2E%2Fboard.sqlite3", "/images/..%2fboard.sqlite3", "/images/" + "0" * 32 + ".png",
                     "/images/" + name.upper(), "/images/" + name + "/", "/images/" + name.replace(".jpg", ".svg"),
                     "/images//" + name, "/images/" + name + "%00.png", "/images/", "/images",
                     "/board.sqlite3", "/server.log", "/images/../server.log"):
            with self.subTest(path=path):
                self.assertEqual(self.raw(base, "GET", path)[0], 404)

        for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "FOO"):
            for path in ("/api/board", task["images"][0], "/"):
                with self.subTest(method=method, path=path):
                    status, response_headers, _ = self.raw(base, method, path)
                    self.assertEqual(status, 405)
                    self.assertEqual(response_headers["Allow"], "GET, HEAD")
        self.assertEqual(self.raw(base, "GET", task["images"][0])[0], 200)

        snapshot = json.loads(self.raw(base, "GET", "/api/board")[2])
        self.assertEqual(snapshot["tasks"][0]["progress"], {"done": 1, "total": 3})
        self.assertEqual(snapshot["tasks"][0]["bot_avatar"], task["bot_avatar"])

    def test_non_loopback_bind_prints_a_warning(self):
        local = self.run_cli("start", "--port", "0")
        self.assertEqual(local.returncode, 0, local.stderr)
        self.assertEqual(local.stderr, "")
        self.assertIn("local_url", json.loads(local.stdout))
        self.call("stop")
        exposed = self.run_cli("start", "--port", "0", "--host", "0.0.0.0")
        self.assertEqual(exposed.returncode, 0, exposed.stderr)
        self.assertIn("Warning", exposed.stderr)
        self.assertIn("trusted network", exposed.stderr)


if __name__ == "__main__":
    unittest.main()
