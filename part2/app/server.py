"""Serve the lab queue over a small, plain-text HTTP API."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app.queue import join, take


class QueueServer(ThreadingHTTPServer):
    request_queue_size = 256


def serve(host: str, port: int, data_dir: str) -> None:
    """Listen until the process is stopped."""
    queue_path = Path(data_dir) / "queue.txt"

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status: int, text: str) -> None:
            body = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/health":
                self.reply(200, "ok")
            else:
                self.reply(404, "not found")

        def do_POST(self) -> None:
            if self.path == "/join":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0:
                        raise ValueError("invalid content length")
                    payload = json.loads(self.rfile.read(length))
                    name = payload.get("name") if isinstance(payload, dict) else None
                    ticket = join(queue_path, name)
                except ValueError:
                    self.reply(400, "invalid name or body")
                else:
                    self.reply(200, str(ticket))
            elif self.path == "/next":
                try:
                    name = take(queue_path)
                except LookupError:
                    self.reply(404, "empty")
                else:
                    self.reply(200, name)
            else:
                self.reply(404, "not found")

    with QueueServer((host, port), Handler) as server:
        server.serve_forever()


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    data_dir = os.environ.get("DATA_DIR", "/data")
    serve("0.0.0.0", port, data_dir)


if __name__ == "__main__":
    main()
