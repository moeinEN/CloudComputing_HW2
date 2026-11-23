"""Serve the lab queue over a small, plain-text HTTP API."""

import json
import os
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import perf_counter

from app.queue import QueueUnavailable, join, take


class QueueServer(ThreadingHTTPServer):
    request_queue_size = 256


def serve(host: str, port: int, data_dir: str) -> None:
    """Listen until the process is stopped."""
    queue_path = Path(data_dir) / "queue.txt"
    enqueue = partial(join, queue_path)
    dequeue = partial(take, queue_path)
    metrics = None
    if redis_url := os.environ.get("REDIS_URL"):
        from app.redis_queue import RedisQueue

        storage = RedisQueue(redis_url)
        enqueue = storage.join
        dequeue = storage.take
        if os.environ.get("QUEUE_METRICS") == "1":
            from app.metrics import QueueMetrics

            metrics = QueueMetrics(storage.length)
            storage.observe = metrics.observe_database

    class Handler(BaseHTTPRequestHandler):
        def handle_one_request(self) -> None:
            self.started_at = perf_counter()
            super().handle_one_request()

        def log_request(self, code="-", size="-") -> None:
            super().log_request(code, size)
            if metrics is not None:
                metrics.observe_http(
                    self.command, getattr(self, "path", ""), code, perf_counter() - self.started_at
                )

        def reply(self, status: int, text: str | bytes,
                  content_type: str = "text/plain; charset=utf-8") -> None:
            body = text.encode("utf-8") if isinstance(text, str) else text
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/health":
                self.reply(200, "ok")
            elif self.path == "/metrics" and metrics is not None:
                body, content_type = metrics.render()
                self.reply(200, body, content_type)
            else:
                self.reply(404, "not found")

        def do_POST(self) -> None:
            try:
                self.post_queue()
            except QueueUnavailable:
                self.reply(503, "queue unavailable")

        def post_queue(self) -> None:
            if self.path == "/join":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0:
                        raise ValueError("invalid content length")
                    payload = json.loads(self.rfile.read(length))
                    name = payload.get("name") if isinstance(payload, dict) else None
                    ticket = enqueue(name)
                except ValueError:
                    self.reply(400, "invalid name or body")
                else:
                    self.reply(200, str(ticket))
            elif self.path == "/next":
                try:
                    name = dequeue()
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
