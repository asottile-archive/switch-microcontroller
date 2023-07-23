from __future__ import annotations

import argparse
import itertools
import time

import cv2
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
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import States
from scripts.engine import Wait
from scripts.engine import Write
from scripts.swsh._bootup import bootup
from scripts.swsh._dialog_shiny_check import dialog
from scripts.swsh._dialog_shiny_check import dialog_shiny_check


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    vid = make_vid()

    moves = itertools.cycle('wasd')

    def next_move(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        Write(next(moves))(vid, ser)

    move_end_t = 0.

    def move_end(vid: object, ser: object) -> None:
        nonlocal move_end_t
        move_end_t = time.monotonic() + .4

    def move_ended(frame: object) -> bool:
        return time.monotonic() >= move_end_t

    timeout_t = 0.

    def timeout_set(vid: object, ser: object) -> None:
        nonlocal timeout_t
        timeout_t = time.monotonic() + 15

    def timeout(frame: object) -> bool:
        return time.monotonic() >= timeout_t

    states: States = {
        **bootup('INITIAL', 'STARTUP'),
        'STARTUP': (
            (always_matches, Press('w', duration=5), 'SET'),
        ),
        'SET': (
            (always_matches, do(timeout_set, next_move, move_end), 'MOVE'),
        ),
        'MOVE': (
            (dialog, Write('0'), 'DIALOG'),
            (timeout, reset, 'INITIAL'),
            (move_ended, do(next_move, move_end), 'MOVE'),
        ),
        **dialog_shiny_check('DIALOG', 'RUN', 'ALARM'),
        'RUN': (
            (
                all_match(
                    match_px(Point(y=652, x=1104), Color(b=234, g=234, r=234)),
                    match_px(Point(y=419, x=1128), Color(b=16, g=16, r=16)),
                    match_text(
                        'Run',
                        Point(y=657, x=1053),
                        Point(y=691, x=1113),
                        invert=False,
                    ),
                ),
                do(Press('w'), Wait(.25), Press('A'), Wait(5)),
                'SET',
            ),
        ),
        **alarm('ALARM', quiet=args.quiet),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=vid, ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
