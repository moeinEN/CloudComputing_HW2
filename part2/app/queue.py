"""Queue stored as one UTF-8 name per line."""

from __future__ import annotations

import fcntl
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def _clean_name(name: str) -> str:
    if not isinstance(name, str) or (name + "\n").splitlines() != [name]:
        raise ValueError("invalid name")
    cleaned = name.strip()
    if not 1 <= len(cleaned) <= 40:
        raise ValueError("invalid name")
    cleaned.encode("utf-8")
    return cleaned


def join(path: str | Path, name: str) -> int:
    """Append a name and return the resulting queue length."""
    cleaned = _clean_name(name)
    path = Path(path)
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            queued = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            queued = ""
        ticket = len(queued.splitlines()) + 1
        with path.open("a", encoding="utf-8") as queue:
            separator = "\n" if queued and not queued.endswith("\n") else ""
            queue.write(f"{separator}{cleaned}\n")
        return ticket


def take(path: str | Path) -> str:
    """Remove and return the oldest name, or raise LookupError."""
    path = Path(path)
    # The sidecar lock keeps the same inode when queue.txt is replaced.
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            names = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            raise LookupError("empty") from None
        if not names:
            raise LookupError("empty")
        first, *rest = names
        temp = NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False)
        try:
            with temp:
                temp.writelines(f"{name}\n" for name in rest)
            os.replace(temp.name, path)
        finally:
            Path(temp.name).unlink(missing_ok=True)
        return first
