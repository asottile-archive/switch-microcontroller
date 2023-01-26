from __future__ import annotations

import cv2
import numpy
import serial

from scripts.engine import get_text
from scripts.engine import getframe
from scripts.engine import match_text
from scripts.engine import Point


class BoxMover:
    def __init__(self) -> None:
        self.box_name = 'unknown'

    def __repr__(self) -> str:
        return f'{type(self).__name__}({self.box_name!r})'

    def record(self, vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        self.box_name = get_text(
            getframe(vid),
            Point(y=85, x=448),
            Point(y=114, x=708),
            invert=True,
        )

    def changed(self, frame: numpy.ndarray) -> bool:
        return not match_text(
            self.box_name,
            Point(y=85, x=448),
            Point(y=114, x=708),
            invert=True,
        )(frame)
