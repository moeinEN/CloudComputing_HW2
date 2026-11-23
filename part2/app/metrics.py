"""Per-process metrics and a live gauge for the shared queue."""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from app.queue import QueueUnavailable


class QueueMetrics:
    def __init__(self, queue_length) -> None:
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "http_requests_total", "HTTP responses", ("method", "route", "status"),
            registry=self.registry,
        )
        self.http_duration = Histogram(
            "http_request_duration_seconds", "HTTP request processing time",
            ("method", "route", "status"),
            buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
            registry=self.registry,
        )
        self.db_duration = Histogram(
            "queue_db_operation_duration_seconds", "Redis command time from the application",
            ("operation",), registry=self.registry,
        )
        Gauge(
            "queue_length", "Number of names in the shared queue", registry=self.registry
        ).set_function(lambda: self.read_length(queue_length))

    @staticmethod
    def read_length(queue_length) -> float:
        try:
            return queue_length()
        except QueueUnavailable:
            return float("nan")

    def observe_http(self, method, path, status, duration) -> None:
        if path == "/metrics":
            return
        route = path if path in {"/health", "/join", "/next"} else "unknown"
        method = method if method in {"GET", "POST"} else "OTHER"
        self.requests.labels(method, route, status).inc()
        self.http_duration.labels(method, route, status).observe(duration)

    def observe_database(self, command, duration) -> None:
        self.db_duration.labels(command).observe(duration)

    def render(self) -> tuple[bytes, str]:
        return generate_latest(self.registry), CONTENT_TYPE_LATEST
