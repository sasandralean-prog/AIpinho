from __future__ import annotations

import threading
from typing import Callable


def run_background(fn: Callable[[], None]) -> threading.Thread:
    thread = threading.Thread(target=fn, daemon=True)
    thread.start()
    return thread
