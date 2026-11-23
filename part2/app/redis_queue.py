"""The optional Redis-backed queue."""

from time import perf_counter

from redis import Redis, RedisError
from redis.backoff import NoBackoff
from redis.retry import Retry

from app.queue import QueueUnavailable, _clean_name


class RedisQueue:
    key = "lab-queue"
    observe = None

    def __init__(self, url: str) -> None:
        self.client = Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry=Retry(NoBackoff(), 0),
        )

    def _query(self, command, *args):
        started_at = perf_counter()
        try:
            return command(self.key, *args)
        except RedisError:
            raise QueueUnavailable("Redis operation failed") from None
        finally:
            if self.observe is not None:
                self.observe(command.__name__, perf_counter() - started_at)

    def join(self, name: str) -> int:
        return self._query(self.client.rpush, _clean_name(name))

    def take(self) -> str:
        name = self._query(self.client.lpop)
        if name is None:
            raise LookupError("empty")
        return name

    def length(self) -> int:
        return self._query(self.client.llen)
