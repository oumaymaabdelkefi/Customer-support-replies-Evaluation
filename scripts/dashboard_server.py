"""
Local interface: the results dashboard plus a "Run tests" tab whose
buttons start the judge, the bias tests and the unit tests, with live
output. Every page load rebuilds the dashboard from results/, so new runs
show up as soon as they finish.

Usage:
    python scripts/dashboard_server.py            # opens http://localhost:8765
    python scripts/dashboard_server.py --port 9000 --no-browser

The Groq key comes from the GROQ_API_KEY environment variable, or can be
typed into the page. A typed key lives only in this process's memory: it
is passed to the run as an environment variable and never written to disk.
The server listens on 127.0.0.1 only, so other machines can't reach it.
Stop it with Ctrl+C.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_dashboard import OUT_PATH, render_html  # noqa: E402

PY = [sys.executable, "-u"]  # -u: unbuffered, so output streams live
NEEDS_KEY = {"judge", "judge_v2", "position", "verbosity", "reply", "adversarial", "pending"}
MAX_LOG_CHARS = 200_000


def latest_padded_run() -> Path | None:
    """Newest results file that judged padded (~pad) items, if any."""
    results = REPO_ROOT / "results"
    candidates = []
    for path in results.glob("llm_judge_*.jsonl"):
        with open(path, encoding="utf-8") as f:
            first = f.readline()
        if '~pad"' in first:
            candidates.append(path)
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def task_commands(task: str, split: str) -> list[list[str]]:
    split_args = ["--split", split] if split in ("dev", "test") else []
    if task == "judge":
        return [PY + ["-m", "harness.run", "--system", "llm_judge", "--items", "data/golden_set.jsonl", *split_args]]
    if task == "pending":
        return [PY + ["scripts/run_pending.py"]]
    if task == "judge_v2":
        return [PY + ["-m", "harness.run", "--system", "llm_judge_v2", "--items", "data/golden_set.jsonl", *split_args]]
    if task == "reply":
        return [PY + ["-m", "harness.run", "--system", "reply_v1", "--items", "data/golden_set.jsonl", *split_args]]
    if task == "adversarial":
        return [PY + ["scripts/make_adversarial_set.py"],
                PY + ["-m", "harness.run", "--system", "llm_judge", "--items", "data/bias/adversarial.jsonl"]]
    if task == "baseline":
        return [PY + ["-m", "harness.run", "--system", "keyword_baseline", "--items", "data/golden_set.jsonl", *split_args]]
    if task == "position":
        return [PY + ["scripts/position_bias.py"]]
    if task == "verbosity":
        # Continue the newest padded run if there is one, so a run cut short
        # by the free-tier daily quota picks up where it stopped tomorrow.
        resume = latest_padded_run()
        resume_args = ["--resume", str(resume.relative_to(REPO_ROOT))] if resume else []
        return [
            PY + ["scripts/verbosity_bias.py", "make", *split_args],
            PY + ["-m", "harness.run", "--system", "llm_judge", "--items", "data/bias/verbosity_padded.jsonl", *resume_args],
        ]
    if task == "tests":
        return [PY + ["-m", "pytest", "tests", "-q"]]
    raise ValueError(f"unknown task {task!r}")


class Runner:
    """Runs one task at a time in a background thread, keeping its output."""

    def __init__(self):
        self.lock = threading.Lock()
        self.task: str | None = None
        self.running = False
        self.exit_code: int | None = None
        self.log = ""
        self.key = os.environ.get("GROQ_API_KEY", "")

    def append(self, text: str):
        with self.lock:
            self.log = (self.log + text)[-MAX_LOG_CHARS:]

    def start(self, task: str, split: str, key: str) -> str | None:
        if key:
            self.key = key
        if task in NEEDS_KEY and not self.key:
            return "This test calls Groq: enter your API key first (or set GROQ_API_KEY)."
        try:
            commands = task_commands(task, split)
        except ValueError as e:
            return str(e)
        with self.lock:
            if self.running:
                return "Another run is still going. Wait for it to finish."
            self.task = f"{task}" + (f" ({split} split)" if split and task not in ("position", "tests") else "")
            self.running, self.exit_code, self.log = True, None, ""
        threading.Thread(target=self._run, args=(commands,), daemon=True).start()
        return None

    def _run(self, commands: list[list[str]]):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        if self.key:
            env["GROQ_API_KEY"] = self.key
        code = 0
        for cmd in commands:
            shown = " ".join(c if c != sys.executable else "python" for c in cmd if c != "-u")
            self.append(f"$ {shown}\n")
            proc = subprocess.Popen(
                cmd, cwd=REPO_ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
            )
            for line in proc.stdout:
                self.append(line)
            code = proc.wait()
            self.append(f"\n[exit code {code}]\n\n")
            if code != 0:
                break
        try:
            html, _ = render_html()
            OUT_PATH.write_text(html, encoding="utf-8")
            self.append("Dashboard rebuilt. Click 'Show new results'.\n")
        except Exception as e:  # noqa: BLE001
            self.append(f"Could not rebuild dashboard: {e}\n")
        with self.lock:
            self.running, self.exit_code = False, code

    def status(self) -> dict:
        with self.lock:
            return {
                "task": self.task, "running": self.running, "exit_code": self.exit_code,
                "log": self.log, "key_set": bool(self.key),
            }


RUNNER = Runner()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: str, content_type: str = "text/plain; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html") or self.path.startswith("/?"):
            try:
                html, _ = render_html()
            except Exception as e:  # noqa: BLE001
                return self._send(500, f"Could not build the dashboard: {e}")
            return self._send(200, html, "text/html; charset=utf-8")
        if self.path == "/status":
            return self._send(200, json.dumps(RUNNER.status()), "application/json")
        self._send(404, "not found")

    def do_POST(self):
        if self.path != "/run":
            return self._send(404, "not found")
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._send(400, "bad request")
        error = RUNNER.start(str(body.get("task", "")), str(body.get("split", "")), str(body.get("key", "")).strip())
        if error:
            return self._send(409, error)
        self._send(200, "started")

    def log_message(self, *args):  # keep the terminal quiet
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://localhost:{args.port}"
    print(f"Interface running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
