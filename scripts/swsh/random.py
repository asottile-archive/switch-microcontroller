from __future__ import annotations

import argparse
import collections
import time

import cv2
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
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import States
from scripts.engine import Wait
from scripts.engine import Write
from scripts.swsh._bootup import bootup
from scripts.swsh._bootup import world
from scripts.swsh._dialog_shiny_check import dialog
from scripts.swsh._dialog_shiny_check import dialog_shiny_check


class Mover:
    def __init__(self) -> None:
        self._t = 0.
        self.todo: collections.deque[tuple[str, float]] = collections.deque()

    def ended(self, frame: object) -> bool:
        return time.monotonic() > self._t

    def move(self, vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        try:
            move, t = self.todo.popleft()
        except IndexError:
            self.todo.extend((s, .4) for s in 'ws')
            move, t = self.todo.popleft()

        ser.write(move.encode())
        self._t = time.monotonic() + t

    def reroute(self, moves: list[tuple[str, float]]) -> None:
        print(f'reroute! {moves}')
        self._t = -1.
        self.todo.clear()
        self.todo.extend(moves)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    mover = Mover()

    timeout_t = 0.

    def timeout_set(vid: object, ser: object) -> None:
        nonlocal timeout_t
        timeout_t = time.monotonic() + 27

    def timeout(frame: object) -> bool:
        return time.monotonic() >= timeout_t

    debounce_t = 0.

    def detect_random(frame: numpy.ndarray) -> bool:
        nonlocal debounce_t
        nonlocal timeout_t

        if time.monotonic() < debounce_t:
            return False

        h = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        m = cv2.inRange(h, (164, 100, 200), (180, 200, 255))
        kernel = numpy.ones((12, 4), numpy.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(
            m, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE,
        )
        # player: Point(y=435, x=654)
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            y += h
            if h / w >= 2 and h * w >= 80:
                my = 'w' if y < 435 else 's'
                dy = abs(435 - y) / 350
                mx = 'a' if x < 655 else 'd'
                dx = abs(655 - x) / 750
                mover.reroute([(my, dy), (mx, dx)])
                debounce_t = time.monotonic() + 1.5
                timeout_t = max(timeout_t, time.monotonic() + 12)
                return True

        return False

    states: States = {
        **bootup('INITIAL', 'STARTUP'),
        'STARTUP': (
            (always_matches, do(), 'SET'),
        ),
        'SET': (
            (always_matches, do(timeout_set, mover.move), 'MOVE'),
        ),
        'MOVE': (
            (dialog, Write('0'), 'DIALOG'),
            (all_match(timeout, world), reset, 'INITIAL'),
            (mover.ended, mover.move, 'MOVE'),
            (detect_random, mover.move, 'MOVE'),
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
        run(vid=make_vid(), ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
