from __future__ import annotations

import argparse
import os
import shutil
import time

import cv2
import numpy
import serial

from scripts.engine import always_matches
from scripts.engine import do
from scripts.engine import get_text
from scripts.engine import make_vid
from scripts.engine import match_text
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import States
from scripts.engine import Wait
from scripts.sv._game_crash import GameCrash
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
    args = parser.parse_args()

    vid = make_vid()

    game_crash = GameCrash()
    reset_time = time.time() - 1

    def needs_clock(frame: object) -> bool:
        return time.time() >= reset_time

    def clock_set(vid: object, ser: object) -> None:
        nonlocal reset_time
        reset_time = time.time() + 20 * 60

    def clock(tl: Point, br: Point, n: int, name: str, end: str) -> States:
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
            name: (
                (eq_n, do(Press('A'), Wait(.1)), end),
                (always_matches, move, name),
            ),
        }

    states: States = {
        'INITIAL': (
            (needs_clock, do(), 'SET_CLOCK'),
            (always_matches, do(), 'BEGIN'),
        ),
        'SET_CLOCK': (
            (
                always_matches,
                do(
                    Press('s'), Wait(1),
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
                'CLOCK_MONTH',
            ),
        ),
        **clock(
            Point(y=441, x=118),
            Point(y=497, x=186),
            3,
            'CLOCK_MONTH',
            'CLOCK_DAY',
        ),
        **clock(
            Point(y=442, x=247),
            Point(y=499, x=313),
            1,
            'CLOCK_DAY',
            'CLOCK_YEAR',
        ),
        **clock(
            Point(y=442, x=390),
            Point(y=497, x=516),
            2023,
            'CLOCK_YEAR',
            'CLOCK_HOUR',
        ),
        **clock(
            Point(y=440, x=607),
            Point(y=503, x=684),
            12,
            'CLOCK_HOUR',
            'CLOCK_MINUTE',
        ),
        **clock(
            Point(y=440, x=735),
            Point(y=499, x=807),
            25,
            'CLOCK_MINUTE',
            'CLOCK_AM',
        ),
        'CLOCK_AM': (
            (
                match_text(
                    'AM',
                    Point(y=442, x=845),
                    Point(y=500, x=937),
                    invert=False,
                ),
                do(
                    Press('A'), Wait(.1), Press('A'), Wait(.5), Press('H'),
                    clock_set,
                ),
                'BEGIN',
            ),
            (always_matches, do(Press('s'), Wait(.1)), 'CLOCK_AM'),
        ),
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
            (nontera_matches, do(), 'RESET'),
            (always_matches, Wait(5.75), 'CHECK'),
        ),
        'CHECK': (
            (nonshiny_matches, do(), 'RESET'),
            (always_matches, do(Press('H'), Wait(1)), 'ALARM'),
        ),
        'RESET': (
            (
                always_matches,
                do(
                    Press('H'), Wait(1),
                    Press('X'), Wait(.5),
                    Press('A'), Wait(2),
                ),
                'INITIAL',
            ),
        ),
        'ALARM': (
            (
                always_matches,
                do(Press('!'), Wait(.25), Press('.'), Wait(.25)),
                'ALARM',
            ),
        ),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=vid, ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
