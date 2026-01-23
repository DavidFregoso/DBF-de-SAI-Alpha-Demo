from __future__ import annotations

from contextlib import contextmanager
import os
import time


def perf_enabled() -> bool:
    return os.getenv("SAI_ALPHA_PERF_LOG", "").strip().lower() in {"1", "true", "yes", "on"}


@contextmanager
def perf_logger(label: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        if perf_enabled():
            duration_ms = (time.perf_counter() - start) * 1000
            print(f"[perf] {label}: {duration_ms:.2f} ms")
