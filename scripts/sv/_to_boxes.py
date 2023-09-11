from __future__ import annotations

from scripts.engine import always_matches
from scripts.engine import Color
from scripts.engine import do
from scripts.engine import match_px
from scripts.engine import match_text
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import States
from scripts.engine import Wait
from scripts.sv._bootup import world


def to_boxes(start: str, end: str) -> States:
    boxes_matches = match_px(Point(y=241, x=1161), Color(b=28, g=183, r=209))

    return {
        start: (
            (world, do(Press('X'), Wait(1)), start),
            (
                match_text(
                    'MAIN MENU',
                    Point(y=116, x=888),
                    Point(y=147, x=1030),
                    invert=True,
                ),
                do(),
                f'{start}_MOVE_RIGHT',
            ),
        ),
        f'{start}_MOVE_RIGHT': (
            (
                match_px(Point(y=156, x=390), Color(b=31, g=190, r=216)),
                do(Press('d'), Wait(.5)),
                f'{start}_MOVE_RIGHT',
            ),
            (always_matches, do(), f'{start}_FIND_BOXES'),
        ),
        f'{start}_FIND_BOXES': (
            (boxes_matches, do(), f'{start}_ENTER_BOXES'),
            (always_matches, do(Press('s'), Wait(.5)), f'{start}_FIND_BOXES'),
        ),
        f'{start}_ENTER_BOXES': (
            (boxes_matches, do(Press('A'), Wait(3)), f'{start}_ENTER_BOXES'),
            (always_matches, do(), end),
        ),
    }
