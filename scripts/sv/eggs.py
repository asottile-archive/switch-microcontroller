from __future__ import annotations

import argparse
import time

import serial

from scripts.engine import all_match
from scripts.engine import always_matches
from scripts.engine import any_match
from scripts.engine import bye
from scripts.engine import Color
from scripts.engine import do
from scripts.engine import make_vid
from scripts.engine import match_px
from scripts.engine import match_text
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import require_tesseract
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import Wait


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--boxes', type=int, default=1)
    args = parser.parse_args()

    require_tesseract()

    start_time = 0.0
    egg_count = 0

    def set_start(vid: object, ser: object) -> None:
        nonlocal start_time
        start_time = time.monotonic()

    def increment_egg_count(vid: object, ser: object) -> None:
        nonlocal egg_count
        egg_count += 1
        print(f'DEBUG: You have {egg_count} eggs currently')

    def restart_eggs(frame: object) -> bool:
        return time.monotonic() > start_time + 30 * 60

    def are_we_done(frame: object) -> bool:
        return egg_count >= args.boxes * 30

    states = {
        'INITIAL': (
            (
                match_px(Point(y=598, x=1160), Color(b=17, g=203, r=244)),
                do(
                    Wait(1),
                    # center camera
                    Press('L'), Wait(.1),
                    # open menu
                    Press('X'), Wait(1), Press('d'), Wait(1),
                ),
                'MENU',
            ),
        ),
        'MENU': (
            (
                match_px(Point(y=292, x=1085), Color(b=30, g=185, r=210)),
                do(
                    # press A on picnic menu
                    Wait(1), Press('A'), Wait(10),
                    # walk up to picnic
                    Press('w', duration=.5),
                    # sandwich time
                    Press('A'), Wait(1.5), Press('A'), Wait(5),
                ),
                'FIND_25',
            ),
            (always_matches, do(Press('s'), Wait(.5)), 'MENU'),
        ),
        'FIND_25': (
            (
                match_text(
                    '25',
                    Point(y=376, x=21),
                    Point(y=403, x=58),
                    invert=True,
                ),
                do(
                    # select sandwich
                    Press('A'), Wait(2),
                    # select pick
                    Press('A'), Wait(10),
                    # cheese 1
                    Press('w', duration=1),
                    Press('s', duration=.2),
                    Press('@', duration=.5),
                    Wait(1),
                    # cheese 2
                    Press('w', duration=1),
                    Press('s', duration=.2),
                    Press('@', duration=.5),
                    Wait(1),
                    # cheese 3
                    Press('w', duration=1),
                    Press('s', duration=.2),
                    Press('@', duration=.5),
                    Wait(3),
                    # bread
                    Press('A'), Wait(3),
                    # pick
                    Press('A'), Wait(10),
                    # confirm
                    Press('A'), Wait(25),
                    # noice
                    Press('A'), Wait(5),
                    # move around the table
                    Wait(.5),
                    Press('d', duration=.1), Wait(.2),
                    Press('L'), Wait(.2),
                    Press('w', duration=.4), Wait(.5),

                    Press('a', duration=.1), Wait(.2),
                    Press('L'), Wait(.2),
                    Press('w', duration=.7), Wait(.5),

                    Press('z', duration=.1), Wait(.2),
                    Press('L'), Wait(.2),
                    Press('w', duration=.5), Wait(.5),

                    Press('A'), Wait(1),
                ),
                'VERIFY_BASKET',
            ),
            (always_matches, do(Press('s'), Wait(1)), 'FIND_25'),
        ),
        'VERIFY_BASKET': (
            (
                match_text(
                    'You peeked inside the basket!',
                    Point(y=546, x=353),
                    Point(y=588, x=706),
                    invert=True,
                ),
                do(set_start, Wait(.1)),
                'MASH_A',
            ),
            (
                # if it fails, go back to the beginning
                always_matches,
                do(
                    Press('B'), Wait(2), Press('Y'),
                    Wait(.5), Press('A'), Wait(5),
                ),
                'INITIAL',
            ),
        ),
        'MASH_A': (
            (
                any_match(
                    match_text(
                        'Do you want to',
                        Point(y=549, x=704),
                        Point(y=590, x=889),
                        invert=True,
                    ),
                    match_text(
                        'Do you want to',
                        Point(y=549, x=658),
                        Point(y=589, x=841),
                        invert=True,
                    ),
                ),
                do(Wait(1), Press('A'), Wait(1)),
                'VERIFY_EGG',
            ),
            (
                all_match(
                    match_px(Point(y=628, x=351), Color(b=49, g=43, r=30)),
                    match_px(Point(y=630, x=893), Color(b=49, g=43, r=30)),
                    match_px(Point(y=546, x=348), Color(b=49, g=43, r=30)),
                ),
                do(Press('A'), Wait(1)),
                'MASH_A',
            ),
            (always_matches, do(), 'WAIT'),
        ),
        'VERIFY_EGG': (
            (
                match_text(
                    'You took the Egg!',
                    Point(y=540, x=351),
                    Point(y=640, x=909),
                    invert=True,
                ),
                do(increment_egg_count, Press('A'), Wait(1)),
                'MASH_A',
            ),
            (always_matches, do(Press('A'), Wait(1)), 'VERIFY_EGG'),
        ),
        'WAIT': (
            (
                are_we_done,
                do(Press('Y'), Wait(.5), Press('A'), Wait(5), bye),
                'EXIT',
            ),
            (
                # if the timer runs out, restart the egg-grabbing sequence
                restart_eggs,
                do(Press('Y'), Wait(.5), Press('A'), Wait(5)),
                'INITIAL',
            ),
            (always_matches, do(Wait(60), Press('A'), Wait(.5)), 'MASH_A'),
        ),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=make_vid(), ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
