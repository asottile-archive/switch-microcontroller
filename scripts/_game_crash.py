from __future__ import annotations

import time

import numpy

from scripts.engine import match_text
from scripts.engine import Point


class GameCrash:
    def __init__(self) -> None:
        self.check_after = 0.
        self.matcher = match_text(
            'The software was closed because an error occurred.',
            Point(y=307, x=306),
            Point(y=351, x=971),
            invert=True,
        )

    def record(self, vid: object, ser: object) -> None:
        self.check_after = time.time() + 30

    def check(self, frame: numpy.ndarray) -> bool:
        return time.time() > self.check_after and self.matcher(frame)
