#!/usr/bin/env python3
"""Agent-owned task board. Python standard library; no remote services."""
from check_runtime import require_runtime

require_runtime()

import argparse
import contextlib
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import URLError
from urllib.request import build_opener, ProxyHandler

STATUSES = ("backlog", "in_progress", "in_review", "blocked", "done")
ASSETS = Path(__file__).resolve().parents[1] / "assets"
LOCAL_HTTP = build_opener(ProxyHandler({}))


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def encode(value):
    return json.dumps(value, ensure_ascii=False)


@contextlib.contextmanager
def connection(state):
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(state / "board.sqlite3", timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS board (id INTEGER PRIMARY KEY, data TEXT NOT NULL, revision INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, data TEXT NOT NULL, revision INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, actor TEXT NOT NULL, message TEXT NOT NULL, at TEXT NOT NULL);
    """)
    try:
        yield db
    finally:
        db.close()


def task_row(row):
    return {**json.loads(row["data"]), "revision": row["revision"]}


def snapshot(state):
    with connection(state) as db:
        db.execute("BEGIN")
        board = db.execute("SELECT * FROM board WHERE id=1").fetchone()
        if not board:
            raise ValueError("Initialize a board first with init.")
        tasks = [task_row(row) for row in db.execute("SELECT * FROM tasks ORDER BY id")]
        events = [dict(row) for row in db.execute("SELECT * FROM events ORDER BY seq DESC LIMIT 150")]
        return {"board": {**json.loads(board["data"]), "revision": board["revision"]},
                "statuses": list(STATUSES), "tasks": tasks, "events": events,
                "history_limit": 150}


def validate_task(task, all_tasks):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", task["id"]):
        raise ValueError("Task ID must be 1–64 letters, numbers, dots, hyphens or underscores.")
    if not task["title"].strip() or len(task["title"]) > 240:
        raise ValueError("Use a nonempty title of at most 240 characters.")
    if task["status"] not in STATUSES:
        raise ValueError("Unknown status.")
    if task["status"] in ("in_progress", "in_review", "done") and not task["assignee"].strip():
        raise ValueError("Assign an agent before starting work.")
    if task["status"] == "in_review" and not task["reviewer"].strip():
        raise ValueError("Name the reviewer when requesting review.")
    if task["status"] == "blocked" and not task["blocker"].strip():
        raise ValueError("Record the blocker and what resolves it.")
    if task["status"] == "done" and not task["evidence"]:
        raise ValueError("Done requires evidence of completion and review.")
    for dep in task["depends_on"]:
        if dep not in all_tasks:
            raise ValueError(f"Unknown dependency: {dep}")
        if task["status"] in ("in_progress", "done") and all_tasks[dep]["status"] != "done":
            raise ValueError(f"Dependency is not done: {dep}")
    graph = {key: value["depends_on"] for key, value in all_tasks.items()}
    graph[task["id"]] = task["depends_on"]
    def visit(key, chain):
        if key in chain:
            raise ValueError("Dependencies cannot form a cycle.")
        for dep in graph.get(key, []):
            visit(dep, chain | {key})
    visit(task["id"], set())


def mutate(state, args):
    if not args.actor or not args.actor.strip():
        raise ValueError("Mutations require --actor (the actual agent identity).")
    with connection(state) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM board WHERE id=1").fetchone()
        if args.command == "init":
            if row:
                raise ValueError("Board already exists; use board to update it.")
            board = {"title": args.title, "goal": args.goal, "mode": "active", "summary": "", "updated_at": now()}
            db.execute("INSERT INTO board VALUES (1, ?, 0)", (encode(board),))
        elif not row:
            raise ValueError("Initialize a board first.")
        else:
            board = json.loads(row["data"])
        result = None
        task_id = getattr(args, "id", None)
        message = getattr(args, "note", None) or args.command
        if args.command == "board":
            for field in ("title", "goal", "mode", "summary"):
                value = getattr(args, field, None)
                if value is not None:
                    board[field] = value
        elif args.command not in ("init", "board"):
            tasks = {row["id"]: task_row(row) for row in db.execute("SELECT * FROM tasks")}
            previous = tasks.get(task_id)
            if args.command == "add":
                if previous:
                    raise ValueError("Task already exists; use edit with its current revision.")
                task = {"id": task_id, "title": args.title, "description": args.description or "",
                        "status": "backlog", "assignee": args.assignee or "", "reviewer": args.reviewer or "",
                        "priority": args.priority or "normal", "depends_on": args.depends_on or [],
                        "criteria": args.criterion or [], "evidence": args.evidence or [], "blocker": "",
                        "created_at": now(), "updated_at": now(), "last_actor": args.actor}
                revision = 1
            else:
                if not previous:
                    raise ValueError("Unknown task ID.")
                if args.expected_revision is not None and previous["revision"] != args.expected_revision:
                    raise ValueError(f"Conflict: current revision is {previous['revision']}; read again before editing.")
                task = dict(previous)
                revision = task.pop("revision") + 1
                if args.command == "claim":
                    if task["status"] not in ("backlog", "blocked"):
                        raise ValueError(f"Cannot claim {task['status']} task owned by {task['assignee']}.")
                    task.update(status="in_progress", assignee=args.actor, blocker="")
                    message = args.note or "Claimed work"
                elif args.command == "move":
                    task["status"] = args.status
                    if args.status != "blocked":
                        task["blocker"] = ""
                    message = args.note or f"Moved to {args.status}"
                for field, flag in (("title", "title"), ("description", "description"), ("assignee", "assignee"),
                                    ("reviewer", "reviewer"), ("priority", "priority"), ("blocker", "blocker"),
                                    ("depends_on", "depends_on"), ("criteria", "criterion")):
                    value = getattr(args, flag, None)
                    if value is not None:
                        task[field] = value
                task["evidence"] += getattr(args, "evidence", None) or []
                task.update(updated_at=now(), last_actor=args.actor)
            validate_task(task, tasks)
            db.execute("INSERT INTO tasks VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET data=excluded.data, revision=excluded.revision",
                       (task_id, encode(task), revision))
            result = {**task, "revision": revision}
        board["updated_at"] = now()
        db.execute("UPDATE board SET data=?, revision=revision+1 WHERE id=1", (encode(board),))
        db.execute("INSERT INTO events(task_id, actor, message, at) VALUES (?, ?, ?, ?)", (task_id, args.actor, message, now()))
        db.commit()
        return result or board


def atomic_json(path, value):
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    temporary.write_text(encode(value) + "\n")
    temporary.replace(path)


def local_url(host, port):
    host = "127.0.0.1" if host == "0.0.0.0" else "::1" if host == "::" else host
    return f"http://{'[' + host + ']' if ':' in host else host}:{port}"


def running(state):
    try:
        info = json.loads((state / "server.json").read_text())
        with LOCAL_HTTP.open(info["local_url"] + "/health", timeout=1) as response:
            health = json.load(response)
        return info if health.get("instance") == info["instance"] else None
    except (OSError, ValueError, URLError):
        return None


def serve(state, args):
    snapshot(state)
    # A lock is held for the entire server lifetime; another start cannot replace
    # metadata or accidentally orphan a process serving this board.
    with (state / "server.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("A server already owns this board.")
        instance = uuid.uuid4().hex
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                route = self.path.split("?", 1)[0]
                etag = None
                if route == "/health":
                    body, content_type = encode({"instance": instance}).encode(), "application/json"
                elif route == "/api/board":
                    view = snapshot(state)
                    etag = '"' + str(view["board"]["revision"]) + '"'
                    if self.headers.get("If-None-Match") == etag:
                        self.send_response(304)
                        self.end_headers()
                        return
                    body, content_type = encode(view).encode(), "application/json"
                elif route in ("/", "/app.js", "/style.css"):
                    file = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}[route]
                    body = (ASSETS / file).read_bytes()
                    content_type = {"/": "text/html", "/app.js": "text/javascript", "/style.css": "text/css"}[route]
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", content_type + "; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-cache")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
                if etag:
                    self.send_header("ETag", etag)
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        class Server(ThreadingHTTPServer):
            address_family = socket.AF_INET6 if ":" in args.host else socket.AF_INET
            daemon_threads = True
        server = Server((args.host, args.port), Handler)
        info = {"pid": os.getpid(), "instance": instance, "host": args.host,
                "port": server.server_port, "local_url": local_url(args.host, server.server_port),
                "public_url": args.public_url or local_url(args.host, server.server_port), "started_at": now()}
        atomic_json(state / "server.json", info)
        def terminate(*_):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, terminate)
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
            (state / "server.json").unlink(missing_ok=True)


def lifecycle(state, args):
    info = running(state)
    if args.command == "status":
        return {"running": bool(info), **(info or {})}
    if args.command == "stop":
        if not info:
            return {"running": False}
        # The responding instance is checked before signaling a recorded PID.
        os.kill(info["pid"], signal.SIGTERM)
        for _ in range(50):
            if not running(state):
                return {"running": False}
            time.sleep(0.1)
        raise ValueError("Server has not stopped; inspect server.log before retrying.")
    if info:
        if args.port not in (0, info["port"]) or args.host != info["host"]:
            raise ValueError("Board is already served at a different address; stop it before changing the bind.")
        return {"running": True, **info}
    snapshot(state)
    command = [sys.executable, str(Path(__file__).resolve()), "--state", str(state), "serve",
               "--host", args.host, "--port", str(args.port)]
    if args.public_url:
        command += ["--public-url", args.public_url]
    with (state / "server.log").open("ab") as log:
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    for _ in range(60):
        info = running(state)
        if info:
            return {"running": True, **info}
        if child.poll() is not None:
            break
        time.sleep(0.1)
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
    raise ValueError("Server did not start; inspect server.log (for example, the port may be occupied).")


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state", default=os.environ.get("AGENT_KANBAN_STATE", str(Path.home() / ".local/state/agent-kanban/default")))
    p.add_argument("--actor", default=os.environ.get("AGENT_KANBAN_ACTOR"))
    commands = p.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--title", required=True)
    init.add_argument("--goal", default="")
    board = commands.add_parser("board")
    for field in ("title", "goal", "summary"):
        board.add_argument("--" + field)
    board.add_argument("--mode", choices=("active", "paused", "complete"))
    for command in ("add", "edit", "move", "claim", "note"):
        sub = commands.add_parser(command)
        sub.add_argument("id")
        sub.add_argument("--note", required=command == "note")
        if command != "add":
            sub.add_argument("--expected-revision", type=int)
        if command in ("add", "edit"):
            sub.add_argument("--title", required=command == "add")
            sub.add_argument("--description")
            sub.add_argument("--priority", choices=("high", "normal", "low"))
            sub.add_argument("--depends-on", nargs="*")
            sub.add_argument("--criterion", action="append")
        if command in ("add", "edit", "move"):
            sub.add_argument("--assignee")
            sub.add_argument("--reviewer")
        if command in ("edit", "move"):
            sub.add_argument("--blocker")
        if command == "move":
            sub.add_argument("--status", choices=STATUSES, required=True)
        sub.add_argument("--evidence", action="append")
    commands.add_parser("list")
    show = commands.add_parser("show")
    show.add_argument("id")
    for name in ("serve", "start"):
        sub = commands.add_parser(name)
        sub.add_argument("--host", default=os.environ.get("AGENT_KANBAN_HOST", "").strip() or "127.0.0.1",
                         help="Bind address: --host overrides AGENT_KANBAN_HOST; default 127.0.0.1")
        sub.add_argument("--port", type=int, default=4317)
        sub.add_argument("--public-url")
    commands.add_parser("status")
    commands.add_parser("stop")
    return p


def main():
    os.umask(0o077)
    args = parser().parse_args()
    state = Path(args.state).expanduser().resolve()
    try:
        if args.command == "serve":
            serve(state, args)
            return
        if args.command in ("start", "stop", "status"):
            result = lifecycle(state, args)
        elif args.command in ("list", "show"):
            result = snapshot(state)
            if args.command == "show":
                result = next((task for task in result["tasks"] if task["id"] == args.id), None)
                if result is None:
                    raise ValueError("Unknown task ID.")
        else:
            result = mutate(state, args)
        print(encode(result))
    except (ValueError, OSError, sqlite3.Error) as error:
        print(encode({"error": str(error)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
