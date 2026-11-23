"""Queue stored as one UTF-8 name per line."""

from __future__ import annotations

from pathlib import Path


def _clean_name(name: str) -> str:
    if not isinstance(name, str) or (name + "\n").splitlines() != [name]:
        raise ValueError("invalid name")
    cleaned = name.strip()
    if not 1 <= len(cleaned) <= 40:
        raise ValueError("invalid name")
    return cleaned


def join(path: str | Path, name: str) -> int:
    """Append a name and return the resulting queue length."""
    cleaned = _clean_name(name)
    path = Path(path)
    try:
        ticket = len(path.read_text(encoding="utf-8").splitlines()) + 1
    except FileNotFoundError:
        ticket = 1
    with path.open("a", encoding="utf-8") as queue:
        queue.write(f"{cleaned}\n")
    return ticket


def take(path: str | Path) -> str:
    """Remove and return the oldest name, or raise LookupError."""
    path = Path(path)
    try:
        first, *rest = path.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, ValueError):
        raise LookupError("empty") from None
    path.write_text("".join(f"{name}\n" for name in rest), encoding="utf-8")
    return first
