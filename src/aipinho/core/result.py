from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Result(Generic[T]):
    ok: bool
    value: T | None = None
    error: str | None = None

    @classmethod
    def success(cls, value: T) -> "Result[T]":
        return cls(ok=True, value=value)

    @classmethod
    def failure(cls, error: str) -> "Result[T]":
        return cls(ok=False, error=error)
