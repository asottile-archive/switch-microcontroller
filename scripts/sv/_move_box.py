from __future__ import annotations

import numpy

from scripts.engine import always_matches
from scripts.engine import do
from scripts.engine import get_text
from scripts.engine import match_text
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import States
from scripts.engine import Wait


def move_box(start: str, end: str, direction: str) -> States:
    box_name = 'unknown'

    def record(frame: numpy.ndarray) -> bool:
        nonlocal box_name
        box_name = get_text(
            frame,
            Point(y=85, x=448),
            Point(y=114, x=708),
            invert=True,
        )
        return True

    def changed(frame: numpy.ndarray) -> bool:
        return not match_text(
            box_name,
            Point(y=85, x=448),
            Point(y=114, x=708),
            invert=True,
        )(frame)

    return {
        start: ((record, do(), f'{start}_DO'),),
        f'{start}_DO': (
            (changed, do(), end),
            (always_matches, do(Press(direction), Wait(.75)), f'{start}_DO'),
        ),
    }
