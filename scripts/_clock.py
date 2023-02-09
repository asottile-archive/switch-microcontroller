from __future__ import annotations

import datetime

import cv2
import numpy
import serial

from scripts.engine import always_matches
from scripts.engine import do
from scripts.engine import get_text
from scripts.engine import match_text
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import States
from scripts.engine import Wait


def clock(dt: datetime.datetime, name: str, end: str) -> States:
    def _state(tl: Point, br: Point, n: int, s: str, e: str) -> States:
        found_n = -1

        def eq_n(frame: numpy.ndarray) -> bool:
            nonlocal found_n
            found_n = int(get_text(frame, tl, br, invert=False))
            return found_n == n

        def move(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
            s = 'w' if n > found_n else 's'
            diff = abs(found_n - n)
            if diff >= 10:
                duration = 1.
            elif diff >= 5:
                duration = .5
            else:
                duration = .1
            do(Press(s, duration=duration), Wait(.1))(vid, ser)

        return {
            s: (
                (eq_n, do(Press('A'), Wait(.1)), e),
                (always_matches, move, s),
            ),
        }

    return {
        name: (
            (
                always_matches,
                do(
                    Press('s'),
                    Press('d', duration=.55),
                    Press('A'), Wait(1),
                    Press('s', duration=1.3),
                    Press('A'), Wait(.75),
                    Press('s', duration=.7),
                    Press('A'), Wait(.75),
                    Press('s'), Press('s'),
                    Press('A'), Wait(.5),
                ),
                f'{name}_MONTH',
            ),
        ),
        **_state(
            Point(y=441, x=118),
            Point(y=497, x=186),
            dt.month,
            f'{name}_MONTH',
            f'{name}_DAY',
        ),

        **_state(
            Point(y=442, x=247),
            Point(y=499, x=313),
            dt.day,
            f'{name}_DAY',
            f'{name}_YEAR',
        ),
        **_state(
            Point(y=442, x=390),
            Point(y=497, x=516),
            dt.year,
            f'{name}_YEAR',
            f'{name}_HOUR',
        ),
        **_state(
            Point(y=440, x=607),
            Point(y=503, x=684),
            int(dt.strftime('%I')),
            f'{name}_HOUR',
            f'{name}_MINUTE',
        ),
        **_state(
            Point(y=440, x=735),
            Point(y=499, x=807),
            dt.minute,
            f'{name}_MINUTE',
            f'{name}_AM',
        ),
        f'{name}_AM': (
            (
                match_text(
                    'AM' if dt.hour < 12 else 'PM',
                    Point(y=442, x=845),
                    Point(y=500, x=937),
                    invert=False,
                ),
                do(Press('A'), Wait(.1), Press('A'), Wait(.5), Press('H')),
                end,
            ),
            (always_matches, do(Press('s'), Wait(.1)), f'{name}_AM'),
        ),
    }
