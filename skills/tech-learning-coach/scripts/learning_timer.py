#!/usr/bin/env python3
"""Local-only learning timer. Python 3.9+, standard library only."""
import argparse
import hmac
import json
import math
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PRODUCT = "learning-coach-timer-v1"
PAGE = Path(__file__).resolve().parent.parent / "assets" / "学习倒计时.html"
LOCK = threading.RLock()
CHILDREN = []


def atomic_json(path, value):
    fd, name = tempfile.mkstemp(prefix=".timer-", dir=str(path.parent))
    try:
        os.chmod(name, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def initial_state():
    return {"status": "idle", "title": "等待下一小节", "lesson_key": "",
            "duration_seconds": 0, "remaining_seconds": 0, "deadline_ms": None,
            "started_at_ms": None, "revision": 0}


class Timer:
    def __init__(self, path):
        self.path = path
        self.state = read_json(path) or initial_state()
        self.active_deadline = None
        if self.state.get("status") == "running":
            seconds = max(0, (self.state["deadline_ms"] - time.time() * 1000) / 1000)
            self.active_deadline = time.time() + seconds

    def view(self):
        with LOCK:
            now = time.time() * 1000
            if self.state["status"] == "running":
                seconds = max(0, self.active_deadline - time.time())
                if seconds <= 0:
                    self.state.update(status="finished", remaining_seconds=0, deadline_ms=None)
                    self.save()
                else:
                    self.state["remaining_seconds"] = seconds
                    self.state["deadline_ms"] = now + seconds * 1000
            return dict(self.state, server_now_ms=now, product=PRODUCT)

    def save(self):
        self.state["revision"] = int(self.state.get("revision", 0)) + 1
        atomic_json(self.path, self.state)

    def change(self, body):
        with LOCK:
            self.view()
            action = body.get("action")
            if action == "start":
                title = body.get("title")
                key = body.get("lesson_key")
                minutes = body.get("minutes")
                if not isinstance(title, str) or not title.strip() or len(title) > 180:
                    raise ValueError("title must contain 1-180 characters")
                if not isinstance(key, str) or not key or len(key) > 200:
                    raise ValueError("lesson_key must contain 1-200 characters")
                if isinstance(minutes, bool) or not isinstance(minutes, (int, float)):
                    raise ValueError("minutes must be a number")
                if not math.isfinite(minutes) or not 0 < minutes <= 240:
                    raise ValueError("minutes must be greater than 0 and at most 240")
                # Idempotent: a repeated request must not silently restart a lesson.
                if key == self.state["lesson_key"]:
                    return self.view()
                duration = round(minutes * 60, 3)
                now = time.time() * 1000
                self.state.update(status="running", title=title.strip(), lesson_key=key,
                                  duration_seconds=duration, remaining_seconds=duration,
                                  started_at_ms=now, deadline_ms=now + duration * 1000)
                self.active_deadline = time.time() + duration
            elif action == "pause":
                if self.state["status"] != "running":
                    return self.view()
                self.state.update(status="paused", deadline_ms=None)
                self.active_deadline = None
            elif action == "resume":
                if self.state["status"] != "paused":
                    return self.view()
                seconds = self.state["remaining_seconds"]
                self.state.update(status="running", deadline_ms=time.time() * 1000 + seconds * 1000)
                self.active_deadline = time.time() + seconds
            elif action == "reset":
                if self.state["duration_seconds"] <= 0:
                    return self.view()
                duration = self.state["duration_seconds"]
                now = time.time() * 1000
                self.state.update(status="running", remaining_seconds=duration,
                                  started_at_ms=now, deadline_ms=now + duration * 1000)
                self.active_deadline = time.time() + duration
            elif action == "stop":
                self.state.update(status="stopped", deadline_ms=None)
                self.active_deadline = None
            else:
                raise ValueError("unknown action")
            self.save()
            return self.view()


def serve(directory):
    token = secrets.token_urlsafe(32)
    timer = Timer(directory / "timer-state.json")
    # Invalidate old connection metadata before publishing a new running instance.
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, code, content, mime="application/json; charset=utf-8"):
            payload = content.encode("utf-8") if isinstance(content, str) else json.dumps(content, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "SAMEORIGIN")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def trusted_host(self):
            return self.headers.get("Host") == server.expected_host

        def do_GET(self):
            if not self.trusted_host():
                return self.reply(403, {"error": "invalid host"})
            if self.path in ("/", "/timer"):
                page = PAGE.read_text(encoding="utf-8")
                page = page.replace('const API_TOKEN = "";', 'const API_TOKEN = ' + json.dumps(token) + ';', 1)
                return self.reply(200, page, "text/html; charset=utf-8")
            if self.path == "/health":
                return self.reply(200, {"product": PRODUCT})
            if self.path == "/api/state":
                return self.reply(200, timer.view())
            return self.reply(404, {"error": "not found"})

        def do_POST(self):
            if not self.trusted_host():
                return self.reply(403, {"error": "invalid host"})
            if not hmac.compare_digest(self.headers.get("X-Timer-Token", ""), token):
                return self.reply(403, {"error": "invalid token"})
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + server.expected_host:
                return self.reply(403, {"error": "cross-origin request refused"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size < 1 or size > 4096:
                    raise ValueError("invalid request length")
                body = json.loads(self.rfile.read(size).decode("utf-8"))
                if not isinstance(body, dict):
                    raise ValueError("JSON object required")
                if self.path == "/api/shutdown":
                    timer.change({"action": "stop"})
                    self.reply(200, {"stopped": True})
                    threading.Thread(target=server.shutdown, daemon=True).start()
                    return
                if self.path != "/api/action":
                    return self.reply(404, {"error": "not found"})
                self.reply(200, timer.change(body))
            except (ValueError, UnicodeDecodeError, KeyError):
                self.reply(400, {"error": "invalid timer request"})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.expected_host = "127.0.0.1:" + str(server.server_port)
    info = {"url": "http://" + server.expected_host, "token": token,
            "pid": os.getpid(), "product": PRODUCT}
    atomic_json(directory / "timer-connection.json", info)
    # No login/startup service. End this task-local process after 8 hours.
    lifetime = threading.Timer(8 * 3600, server.shutdown)
    lifetime.daemon = True
    lifetime.start()
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
        current = read_json(directory / "timer-connection.json")
        if current.get("token") == token:
            (directory / "timer-connection.json").unlink(missing_ok=True)


def request(info, route, body=None):
    headers = {"Accept": "application/json"}
    payload = None
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers.update({"Content-Type": "application/json", "X-Timer-Token": info["token"]})
    req = Request(info["url"] + route, data=payload, headers=headers)
    with urlopen(req, timeout=3) as response:
        return json.load(response)


def connect(directory, create):
    info = read_json(directory / "timer-connection.json")
    if info.get("product") == PRODUCT and info.get("url", "").startswith("http://127.0.0.1:"):
        try:
            if request(info, "/health").get("product") == PRODUCT:
                return info
        except (OSError, ValueError, URLError):
            pass
    if not create:
        raise RuntimeError("timer server is not running")
    if not PAGE.is_file():
        raise RuntimeError("timer HTML asset is missing")
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    log = open(directory / "timer-server.log", "ab")
    try:
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "serve", "--state-dir", str(directory)],
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                 start_new_session=True)
        CHILDREN.append(child)
    finally:
        log.close()
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        info = read_json(directory / "timer-connection.json")
        if info.get("pid") == child.pid:
            try:
                if request(info, "/health").get("product") == PRODUCT:
                    return info
            except (OSError, ValueError, URLError):
                pass
        if child.poll() is not None:
            break
        time.sleep(0.1)
    raise RuntimeError("timer failed to start; inspect the local server log")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["serve", "ensure", "start", "status", "pause", "resume", "reset", "stop", "shutdown"])
    parser.add_argument("--state-dir", type=Path, required=True, help="Task-local private state directory, never inside the skill or repository")
    parser.add_argument("--minutes", type=float)
    parser.add_argument("--title")
    parser.add_argument("--lesson-key")
    args = parser.parse_args()
    directory = args.state_dir.expanduser().resolve()
    if args.command == "serve":
        serve(directory)
        return
    if args.command == "start" and (args.minutes is None or not args.title or not args.lesson_key):
        parser.error("start requires --minutes, --title, --lesson-key")
    info = connect(directory, args.command in ("start", "ensure"))
    if args.command in ("ensure", "status"):
        state = request(info, "/api/state")
    elif args.command == "shutdown":
        state = request(info, "/api/shutdown", {})
    else:
        body = {"action": args.command}
        if args.command == "start":
            body.update(minutes=args.minutes, title=args.title, lesson_key=args.lesson_key)
        state = request(info, "/api/action", body)
    print(json.dumps({"url": info["url"] + "/timer", "state": state}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, HTTPError) as error:
        print("Timer error: " + str(error), file=sys.stderr)
        sys.exit(1)
