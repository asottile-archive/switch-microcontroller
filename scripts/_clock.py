from __future__ import annotations

import argparse
import datetime

import cv2
import numpy
import serial

from scripts.engine import always_matches
from scripts.engine import bye
from scripts.engine import do
from scripts.engine import get_text
from scripts.engine import getframe
from scripts.engine import make_vid
from scripts.engine import match_text
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import States
from scripts.engine import Wait

_TO_CLOCK = do(
    Press('s'),
    Press('d', duration=.55),
    Press('A'), Wait(1),
    Press('s', duration=1.3),
    Press('A'), Wait(.75),
    Press('s', duration=.7),
    Press('A'), Wait(.75),
)


def current_dt(vid: cv2.VideoCapture, ser: serial.Serial) -> datetime.datetime:
    _TO_CLOCK(vid, ser)

    text = get_text(
        getframe(vid),
        Point(y=370, x=815),
        Point(y=401, x=1048),
        invert=False,
    )
    date, time, ampm = text.lower().replace('.', '').split()
    month_s, day_s, year_s = date.split('/')
    hour_s, minute_s = time.split(':')

    hour = int(hour_s) % 12
    if ampm == 'pm':
        hour += 12

    ret = datetime.datetime(
        year=int(year_s),
        month=int(month_s),
        day=int(day_s),
        hour=hour,
        minute=int(minute_s),
    )

    do(Press('H'), Wait(1))(vid, ser)

    return ret


def clock(dt: datetime.datetime, name: str, end: str) -> States:
    def _state(tl: Point, br: Point, n: int, s: str, e: str) -> States:
        found_n = -1

        def eq_n(frame: numpy.ndarray) -> bool:
            nonlocal found_n
            # ocr sometimes has problems with `07` as `O07`
            n_s = get_text(frame, tl, br, invert=False).lstrip('O0o') or '0'
            found_n = int(n_s)
            return found_n == n

        def move(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
            s = 'w' if n > found_n else 's'
            diff = abs(found_n - n)
            if diff >= 10:
                duration = .8
            elif diff >= 5:
                duration = .4
            else:
                duration = .1
            do(Press(s, duration=duration), Wait(.3))(vid, ser)

        return {
            s: (
                (eq_n, do(Press('A'), Wait(.1)), e),
                (always_matches, move, s),
            ),
        }

    return {
        name: (
            (
                always_matches,
                do(_TO_CLOCK, Press('s'), Press('s'), Press('A'), Wait(.5)),
                f'{name}_MONTH',
            ),
        ),
        **_state(
            Point(y=441, x=118),
            Point(y=497, x=186),
            dt.month,
            f'{name}_MONTH',
            f'{name}_DAY',
        ),

        **_state(
            Point(y=442, x=247),
            Point(y=499, x=313),
            dt.day,
            f'{name}_DAY',
            f'{name}_YEAR',
        ),
        **_state(
            Point(y=442, x=390),
            Point(y=497, x=516),
            dt.year,
            f'{name}_YEAR',
            f'{name}_HOUR',
        ),
        **_state(
            Point(y=440, x=607),
            Point(y=503, x=684),
            int(dt.strftime('%I')),
            f'{name}_HOUR',
            f'{name}_MINUTE',
        ),
        **_state(
            Point(y=440, x=735),
            Point(y=499, x=807),
            dt.minute,
            f'{name}_MINUTE',
            f'{name}_AM',
        ),
        f'{name}_AM': (
            (
                match_text(
                    'AM' if dt.hour < 12 else 'PM',
                    Point(y=442, x=845),
                    Point(y=500, x=937),
                    invert=False,
                ),
                do(Press('A'), Wait(.1), Press('A'), Wait(.5), Press('H')),
                end,
            ),
            (always_matches, do(Press('s'), Wait(.3)), f'{name}_AM'),
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('dt', type=datetime.datetime.fromisoformat)
    args = parser.parse_args()

    states: States = {
        **clock(args.dt, 'INITIAL', 'END'),
        'END': ((always_matches, bye, 'UNREACHABLE'),),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=make_vid(), ser=ser, initial='INITIAL', states=states)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
