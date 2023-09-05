from __future__ import annotations

import time

import numpy

from scripts.engine import always_matches
from scripts.engine import do
from scripts.engine import Point
from scripts.engine import States


def dialog(frame: numpy.ndarray) -> bool:
    tl1 = Point(y=587, x=22).norm(frame.shape)
    br1 = Point(y=604, x=40).norm(frame.shape)

    tl2 = Point(y=587, x=1183).norm(frame.shape)
    br2 = Point(y=604, x=1200).norm(frame.shape)

    return (
        numpy.all(frame[tl1.y:br1.y, tl1.x:br1.x] == (48, 48, 48)) and
        numpy.all(frame[tl2.y:br2.y, tl2.x:br2.x] == (59, 59, 59))
    )


def dialog_shiny_check(
        begin: str,
        end: str,
        alarm: str,
        *,
        cutoff: float = 1.,
) -> States:
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
        return t1 - t0 > cutoff

    return {
        begin: (
            (dialog, record_start, begin),
            (always_matches, do(), f'{begin}__SHINY_ANIMATION_END'),
        ),
        f'{begin}__SHINY_ANIMATION_END': (
            (dialog, record_end, f'{begin}__SHINY_CHECK'),
        ),
        f'{begin}__SHINY_CHECK': (
            (is_shiny, do(), alarm),
            (always_matches, do(), end),
        ),
    }
