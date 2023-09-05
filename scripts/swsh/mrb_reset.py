from __future__ import annotations

import argparse
import contextlib
import datetime
import time

import cv2
import numpy
import serial

from scripts._clock import clock
from scripts._clock import current_dt
from scripts._reset import reset
from scripts.engine import all_match
from scripts.engine import always_matches
from scripts.engine import any_match
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
from scripts.swsh._bootup import bootup
from scripts.swsh._bootup import game_start
from scripts.swsh._bootup import world


class Done(RuntimeError):
    pass


def done(vid: object, ser: object) -> None:
    raise Done


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--quiet', action='store_true')
    parser.add_argument(
        '--stars',
        choices=(3, 4, 5),
        type=int,
        required=True,
        action='append',
    )
    args = parser.parse_args()

    dt = datetime.datetime.today()

    def determine_date(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        nonlocal dt
        dt = current_dt(vid, ser).replace(hour=1, minute=0)
        print(f'current date is {dt.date()}')

    def increment_date(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        nonlocal dt
        dt = dt + datetime.timedelta(days=1)

        states: States = {
            **clock(dt, 'CLOCK_INITIAL', 'CLOCK_END'),
            'CLOCK_END': ((always_matches, done, 'UNREACHABLE'),),
        }

        with contextlib.suppress(Done):
            run(vid=vid, ser=ser, initial='CLOCK_INITIAL', states=states)

    try_ore = any_match(
        world,
        all_match(
            match_px(Point(y=10, x=1083), Color(b=47, g=175, r=218)),
            match_px(Point(y=10, x=1104), Color(b=18, g=164, r=200)),
        ),
    )

    invite_others = all_match(
        match_px(Point(y=457, x=1180), Color(b=16, g=16, r=16)),
        match_text(
            'Invite Others',
            Point(y=440, x=931),
            Point(y=472, x=1093),
            invert=True,
        ),
    )

    ready_to_battle = all_match(
        match_px(Point(y=568, x=1150), Color(b=16, g=16, r=16)),
        match_text(
            'Ready to Battle!',
            Point(y=494, x=902),
            Point(y=531, x=1114),
            invert=False,
        ),
    )

    def do_increment_date(start: str, end: str) -> States:
        return {
            start: (
                (try_ore, do(Press('A'), Wait(.75)), start),
                (invite_others, do(Press('A'), Wait(1)), f'{start}__WAIT'),
            ),
            f'{start}__WAIT': (
                (
                    ready_to_battle,
                    do(Wait(1), Press('H'), Wait(1), increment_date),
                    f'{start}__WAIT_FOR_HOME',
                ),
            ),
            f'{start}__WAIT_FOR_HOME': (
                (
                    all_match(
                        match_px(
                            Point(y=705, x=13),
                            Color(b=217, g=217, r=217),
                        ),
                        match_text(
                            'Continue',
                            Point(y=668, x=1113),
                            Point(y=703, x=1224),
                            invert=False,
                        ),
                    ),
                    do(Press('A'), Wait(.5)),
                    f'{start}__WAIT_FOR_RETURN',
                ),
            ),
            f'{start}__WAIT_FOR_RETURN': (
                (
                    ready_to_battle,
                    do(Wait(1), Press('B'), Wait(.75), Press('A'), Wait(1)),
                    end,
                ),
            ),
        }

    star_matchers = (
        match_px(Point(y=58, x=70), Color(b=234, g=234, r=234)),
        match_px(Point(y=60, x=130), Color(b=234, g=233, r=235)),
        match_px(Point(y=60, x=191), Color(b=234, g=236, r=230)),
        match_px(Point(y=59, x=254), Color(b=236, g=235, r=231)),
        match_px(Point(y=60, x=314), Color(b=234, g=234, r=234)),
    )

    def stars(n: int) -> Matcher:
        def stars_impl(frame: numpy.ndarray) -> bool:
            return all_match(*star_matchers[:n])(frame)
        return stars_impl

    def requested(n: int) -> Matcher:
        def requested_impl(frame: numpy.ndarray) -> bool:
            return n in args.stars
        return requested_impl

    seen: list[numpy.ndarray] = []

    def check(frame: numpy.ndarray) -> bool:
        tl = Point(y=287, x=207)
        br = Point(y=476, x=408)
        crop = frame[tl.y:br.y, tl.x:br.x]

        for img in seen:
            if numpy.array_equal(img, crop):
                print('already seen!')
                return False

        ser.write(b'!')
        time.sleep(.1)
        ser.write(b'.')
        try:
            input('is this the right raid? (enter to skip, ^D to exit)')
        except (EOFError, KeyboardInterrupt):
            print('\nbye!')
            raise SystemExit(0)
        else:
            seen.append(crop)
            return False

    states: States = {
        'INITIAL': (
            (game_start, determine_date, 'BOOTUP'),
        ),
        **bootup('BOOTUP', 'SKIP1'),
        **do_increment_date('SKIP1', 'SKIP2'),
        **do_increment_date('SKIP2', 'SKIP3'),
        **do_increment_date('SKIP3', 'TO_DEN'),
        'TO_DEN': (
            (try_ore, do(Press('A'), Wait(.75)), 'TO_DEN'),
            (invite_others, do(), 'CHECK'),
        ),
        'CHECK': (
            (all_match(stars(5), requested(5), check), do(), 'UNREACHABLE'),
            (stars(5), do(), 'RESET'),
            (all_match(stars(4), requested(4), check), do(), 'UNREACHABLE'),
            (stars(4), do(), 'RESET'),
            (all_match(stars(3), requested(3), check), do(), 'UNREACHABLE'),
            (stars(3), do(), 'RESET'),
        ),
        'RESET': (
            (always_matches, reset, 'BOOTUP'),
        ),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=make_vid(), ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
