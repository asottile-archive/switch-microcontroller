from __future__ import annotations

import argparse
import datetime
import os
import shutil
import time

import cv2
import numpy
import serial

from scripts._alarm import alarm
from scripts._clock import clock
from scripts._game_crash import GameCrash
from scripts._reset import reset
from scripts.engine import always_matches
from scripts.engine import do
from scripts.engine import make_vid
from scripts.engine import match_text
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import States
from scripts.engine import Wait
from scripts.sv._pixels import world_matches


def nontera_matches(frame: numpy.ndarray) -> bool:
    tl = Point(y=256, x=657)
    br = Point(y=266, x=666)
    return numpy.average(frame[tl.y:br.y, tl.x:br.x]) < 220


def nonshiny_matches(frame: numpy.ndarray) -> bool:
    cv2.imwrite('img.png', frame)
    tl = Point(y=83, x=645).norm(frame.shape)
    br = Point(y=120, x=674).norm(frame.shape)
    crop = frame[tl.y:br.y, tl.x:br.x]
    os.makedirs('crops', exist_ok=True)
    cv2.imwrite('crop.png', crop)
    shutil.copy('crop.png', f'crops/crop-{int(time.time())}.png')
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    thres = cv2.inRange(hsv, (2, 25, 25), (7, 255, 255))
    cv2.imwrite('thres.png', thres)
    count = numpy.count_nonzero(thres)
    print(f'matched: {count}')
    return count >= 300


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    vid = make_vid()

    game_crash = GameCrash()
    reset_time = time.time() - 1

    def needs_clock(frame: object) -> bool:
        return time.time() >= reset_time

    def clock_set(vid: object, ser: object) -> None:
        nonlocal reset_time
        reset_time = time.time() + 20 * 60

    states: States = {
        'INITIAL': (
            (needs_clock, Wait(1), 'CLOCK'),
            (always_matches, do(), 'BEGIN'),
        ),
        **clock(datetime.datetime(2023, 3, 1, 0, 25), 'CLOCK', 'CLOCK_DONE'),
        'CLOCK_DONE': ((always_matches, clock_set, 'BEGIN'),),
        'BEGIN': (
            (
                match_text(
                    'Start',
                    Point(y=669, x=1158),
                    Point(y=700, x=1228),
                    invert=False,
                ),
                do(Press('A'), Wait(1)),
                'BEGIN',
            ),
            (
                match_text(
                    'Select a user.',
                    Point(y=336, x=60),
                    Point(y=378, x=240),
                    invert=False,
                ),
                do(Press('A'), Wait(1)),
                'START',
            ),
        ),
        'START': (
            (
                match_text(
                    'PRESS',
                    Point(y=489, x=802),
                    Point(y=530, x=898),
                    invert=True,
                ),
                do(Wait(2), Press('A'), Wait(1), game_crash.record),
                'WORLD',
            ),
        ),
        'WORLD': (
            (world_matches, Wait(.5), 'CHECK_TERA'),
            (game_crash.check, do(Press('A'), Wait(1)), 'INITIAL'),
        ),
        'CHECK_TERA': (
            (nontera_matches, reset, 'INITIAL'),
            (always_matches, Wait(5.75), 'CHECK'),
        ),
        'CHECK': (
            (nonshiny_matches, reset, 'INITIAL'),
            (always_matches, do(Press('H'), Wait(1)), 'ALARM'),
        ),
        **alarm('ALARM', quiet=args.quiet),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=vid, ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
