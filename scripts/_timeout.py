from __future__ import annotations

import time

from scripts.engine import Action


class Timeout:
    def __init__(self) -> None:
        self.end = 0.

    def after(self, t: float) -> Action:
        def after_impl(vid: object, ser: object) -> None:
            self.end = time.monotonic() + t
        return after_impl

    def expired(self, frame: object) -> bool:
        return time.monotonic() > self.end
