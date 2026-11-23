from collections import deque
from unittest.mock import Mock

import pytest
from redis import ConnectionError

from app.metrics import QueueMetrics
from app.queue import QueueUnavailable
from app.redis_queue import RedisQueue


def test_redis_queue_contract(monkeypatch):
    names = deque()

    def rpush(_key, name):
        names.append(name)
        return len(names)

    client = Mock()
    client.rpush.side_effect = rpush
    client.lpop.side_effect = lambda _key: names.popleft() if names else None
    monkeypatch.setattr("app.redis_queue.Redis.from_url", lambda *_args, **_kwargs: client)
    queue = RedisQueue("redis://db:6379/0")

    for invalid in (" ", "a" * 41, "Ali\n"):
        with pytest.raises(ValueError):
            queue.join(invalid)
    client.rpush.assert_not_called()

    assert queue.join("  نگار  ") == 1
    assert queue.join("Sara") == 2
    assert queue.take() == "نگار"
    assert queue.join("Ali") == 2
    assert [queue.take(), queue.take()] == ["Sara", "Ali"]
    with pytest.raises(LookupError):
        queue.take()

    client.llen.side_effect = ConnectionError("unavailable")
    with pytest.raises(QueueUnavailable):
        queue.length()


def test_metrics_bound_labels_and_keep_scraping_after_outage():
    read_length = Mock(return_value=3)
    metrics = QueueMetrics(read_length)
    metrics.observe_http("POST", "/join", 400, 0.012)
    metrics.observe_http("POST", "/join", 503, 0.12)
    metrics.observe_http("UNKNOWN", "/user/Ali", 404, 0.001)
    metrics.observe_http("GET", "/metrics", 200, 0.001)
    metrics.observe_database("rpush", 0.1)

    payload, _ = metrics.render()
    assert b'http_requests_total{method="POST",route="/join",status="400"} 1.0' in payload
    assert b'http_requests_total{method="POST",route="/join",status="503"} 1.0' in payload
    assert b'http_requests_total{method="OTHER",route="unknown",status="404"} 1.0' in payload
    assert b"/user/Ali" not in payload
    assert b'route="/metrics"' not in payload
    assert b'queue_db_operation_duration_seconds_count{operation="rpush"} 1.0' in payload
    assert b"queue_length 3.0" in payload

    read_length.side_effect = QueueUnavailable()
    assert b"queue_length NaN" in metrics.render()[0]
