from __future__ import annotations

import argparse
import time

import cv2
import serial

from scripts.engine import all_match
from scripts.engine import always_matches
from scripts.engine import Color
from scripts.engine import do
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
    args = parser.parse_args()

    require_tesseract()

    vid = cv2.VideoCapture(0)
    vid.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    vid.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    start_time = 0.0

    def set_start(vid: object, ser: object) -> None:
        nonlocal start_time
        start_time = time.monotonic()

    def are_we_done(frame: object) -> bool:
        return time.monotonic() > start_time + 30 * 60

    def bye(vid: object, ser: object) -> None:
        raise SystemExit

    states = {
        'INITIAL': (
            (
                match_px(Point(y=399, x=696), Color(b=17, g=203, r=244)),
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
                match_px(Point(y=195, x=651), Color(b=30, g=185, r=210)),
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
                    Point(y=251, x=13),
                    Point(y=269, x=35),
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
                    Point(y=364, x=212),
                    Point(y=392, x=424),
                    invert=True,
                ),
                do(set_start, Wait(.1)),
                'MASH_A',
            ),
            (
                always_matches,
                do(Press('!'), Wait(.5), Press('.')),
                'INVALID',
            ),
        ),
        'MASH_A': (
            (
                all_match(
                    match_px(Point(y=419, x=211), Color(b=49, g=43, r=30)),
                    match_px(Point(y=420, x=536), Color(b=49, g=43, r=30)),
                    match_px(Point(y=364, x=209), Color(b=49, g=43, r=30)),
                ),
                do(Press('A'), Wait(.5)),
                'MASH_A',
            ),
            (always_matches, do(), 'WAIT'),
        ),
        'WAIT': (
            (
                are_we_done,
                do(Press('Y'), Wait(.5), Press('A'), Wait(5), bye),
                'EXIT',  # TODO: loop?
            ),
            (always_matches, do(Wait(60), Press('A'), Wait(.5)), 'MASH_A'),
        ),
    }

    with serial.Serial(args.serial, 9600) as ser:
        try:
            run(vid=vid, ser=ser, initial='INITIAL', states=states)
        except KeyboardInterrupt:
            __import__('pdb').post_mortem()
            raise


if __name__ == '__main__':
    raise SystemExit(main())
