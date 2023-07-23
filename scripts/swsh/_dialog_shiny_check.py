from __future__ import annotations

import time

from scripts.engine import all_match
from scripts.engine import always_matches
from scripts.engine import Color
from scripts.engine import do
from scripts.engine import match_px_exact
from scripts.engine import Point
from scripts.engine import States

dialog = all_match(
    match_px_exact(Point(y=587, x=20), Color(b=48, g=48, r=48)),
    match_px_exact(Point(y=672, x=1233), Color(b=48, g=48, r=48)),
    match_px_exact(Point(y=683, x=1132), Color(b=59, g=59, r=59)),
    match_px_exact(Point(y=587, x=107), Color(b=59, g=59, r=59)),
)


def dialog_shiny_check(begin: str, end: str, alarm: str) -> States:
    t0 = t1 = 0.

    def record_start(vid: object, ser: object) -> None:
        nonlocal t0
        t0 = time.monotonic()

    def record_end(vid: object, ser: object) -> None:
        nonlocal t1
        t1 = time.monotonic()

    def is_shiny(frame: object) -> bool:
        print(f'delay: {t1 - t0:.3f}')
        if t1 - t0 >= 8:
            raise AssertionError('fuckup')
        return t1 - t0 > 1

    return {
        begin: (
            (dialog, record_start, begin),
            (always_matches, do(), 'SHINY_ANIMATION_END'),
        ),
        'SHINY_ANIMATION_END': (
            (dialog, record_end, 'SHINY_CHECK'),
        ),
        'SHINY_CHECK': (
            (is_shiny, do(), alarm),
            (always_matches, do(), end),
        ),
    }
