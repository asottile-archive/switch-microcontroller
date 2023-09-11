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
from scripts._reset import reset
from scripts.engine import always_matches
from scripts.engine import do
from scripts.engine import make_vid
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import States
from scripts.engine import Wait
from scripts.sv._bootup import bootup


def nontera_matches(frame: numpy.ndarray) -> bool:
    tl = Point(y=504, x=318)
    br = Point(y=516, x=328)
    return numpy.average(frame[tl.y:br.y, tl.x:br.x]) < 235


def nonshiny_matches(frame: numpy.ndarray) -> bool:
    cv2.imwrite('img.png', frame)
    tl = Point(y=411, x=191)
    br = Point(y=553, x=313)
    crop = frame[tl.y:br.y, tl.x:br.x]
    os.makedirs('crops', exist_ok=True)
    cv2.imwrite('crop.png', crop)
    shutil.copy('crop.png', f'crops/crop-{int(time.time())}.png')
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    thres = cv2.inRange(hsv, (95, 2, 25), (125, 150, 255))
    cv2.imwrite('thres.png', thres)
    count = numpy.count_nonzero(thres)
    print(f'matched: {count}')
    return count >= 2200


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    reset_time = time.monotonic() - 1

    def needs_clock(frame: object) -> bool:
        return time.monotonic() >= reset_time

    def clock_set(vid: object, ser: object) -> None:
        nonlocal reset_time
        reset_time = time.monotonic() + 20 * 60

    states: States = {
        'INITIAL': (
            (needs_clock, Wait(1), 'CLOCK'),
            (always_matches, do(), 'BEGIN'),
        ),
        **clock(datetime.datetime(2023, 3, 2, 0, 25), 'CLOCK', 'CLOCK_DONE'),
        'CLOCK_DONE': (
            (always_matches, clock_set, 'BEGIN'),
        ),
        **bootup('BEGIN', 'WORLD', 'INITIAL'),
        'WORLD': (
            (always_matches, Wait(.2), 'CHECK_TERA'),
        ),
        'CHECK_TERA': (
            (nontera_matches, reset, 'INITIAL'),
            (always_matches, Wait(.6), 'CHECK'),
        ),
        'CHECK': (
            (nonshiny_matches, reset, 'INITIAL'),
            (always_matches, do(Press('H'), Wait(1)), 'ALARM'),
        ),
        **alarm('ALARM', quiet=args.quiet),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=make_vid(), ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
