from __future__ import annotations

import argparse
import time

import numpy
import serial

from scripts._alarm import alarm
from scripts._reset import reset
from scripts.engine import all_match
from scripts.engine import always_matches
from scripts.engine import Color
from scripts.engine import do
from scripts.engine import make_vid
from scripts.engine import match_px
from scripts.engine import match_text
from scripts.engine import Matcher
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import States
from scripts.engine import Wait


def match_exact(px: Point, c: Color) -> Matcher:
    def match_exact_impl(frame: numpy.ndarray) -> bool:
        pt = px.norm(frame.shape)
        return numpy.array_equal(frame[pt.y][pt.x], c)
    return match_exact_impl


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    vid = make_vid()

    dialog = all_match(
        match_exact(Point(y=587, x=20), Color(b=48, g=48, r=48)),
        match_exact(Point(y=672, x=1233), Color(b=48, g=48, r=48)),
        match_exact(Point(y=683, x=1132), Color(b=59, g=59, r=59)),
        match_exact(Point(y=587, x=107), Color(b=59, g=59, r=59)),
    )

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

    states: States = {
        'INITIAL': (
            (
                all_match(
                    match_px(Point(y=61, x=745), Color(b=217, g=217, r=217)),
                    match_text(
                        'Start',
                        Point(y=669, x=1158),
                        Point(y=700, x=1228),
                        invert=False,
                    ),
                ),
                do(Press('A'), Wait(1.5)),
                'SELECT_USER',
            ),
        ),
        'SELECT_USER': (
            (
                match_text(
                    'Select a user.',
                    Point(y=336, x=60),
                    Point(y=378, x=240),
                    invert=False,
                ),
                do(Press('A'), Wait(1)),
                'WAIT_FOR_START',
            ),
        ),
        'WAIT_FOR_START': (
            (
                match_exact(Point(5, 5), Color(b=16, g=16, r=16)),
                do(),
                'START',
            ),
            (
                match_text(
                    'Downloadable content cannot be played.',
                    Point(y=266, x=374),
                    Point(y=312, x=904),
                    invert=False,
                ),
                do(Press('a'), Wait(.2), Press('A'), Wait(.5)),
                'INITIAL',
            ),
        ),
        'START': (
            (
                match_exact(Point(5, 5), Color(b=16, g=16, r=16)),
                do(),
                'START',
            ),
            (
                always_matches,
                do(Wait(.5), Press('A'), Wait(1), Press('A')),
                'WORLD',
            ),
        ),
        'WORLD': (
            (
                all_match(
                    match_px(Point(y=701, x=31), Color(b=239, g=88, r=44)),
                    match_px(Point(y=701, x=14), Color(b=234, g=234, r=234)),
                ),
                do(),
                'WAIT_FOR_DIALOG',
            ),
        ),
        'WAIT_FOR_DIALOG': (
            (dialog, do(), 'DIALOG'),
            (always_matches, do(), 'WAIT_FOR_DIALOG'),
        ),
        'DIALOG': (
            (dialog, record_start, 'DIALOG'),
            (always_matches, do(), 'ANIMATION_END'),
        ),
        'ANIMATION_END': (
            (dialog, record_end, 'CHECK'),
        ),
        'CHECK': (
            (is_shiny, do(), 'ALARM'),
            (always_matches, reset, 'INITIAL'),
        ),
        **alarm('ALARM', quiet=args.quiet),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=vid, ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
