from __future__ import annotations

import argparse

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
    parser.add_argument('--boxes', type=int, required=True)
    args = parser.parse_args()

    require_tesseract()

    vid = cv2.VideoCapture(0)
    vid.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    vid.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    box = 0
    column = 0
    eggs = 5

    select = do(
        Press('-'), Wait(.5), Press('s', duration=.8), Wait(.4),
        Press('A'), Wait(.5),
    )

    def eggs_done(frame: object) -> bool:
        return eggs == 0

    def egg_hatched(vid: object, ser: object) -> None:
        nonlocal eggs
        eggs -= 1

    def start_left(vid: object, ser: serial.Serial) -> None:
        ser.write(b'#')

    def move_to_column(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        for _ in range(column):
            do(Press('d'), Wait(.4))(vid, ser)

    def pick_up_new_column(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        nonlocal box, column, eggs
        eggs = 5
        if column == 5:
            column = 0
            box += 1
            do(
                Press('R'), Wait(.5),
                Press('d'), Wait(.4),
                Press('d'), Wait(.4),
            )(vid, ser)
        else:
            column += 1
            do(Press('d'), Wait(.5))(vid, ser)

        select(vid, ser)

        for _ in range(column + 1):
            do(Press('a'), Wait(.4))(vid, ser)

        do(Press('s'), Wait(.4), Press('A'), Wait(.5))(vid, ser)

    def done(frame: object) -> bool:
        return box == args.boxes - 1 and column == 5 and eggs == 0

    def bye(vid: object, ser: object) -> None:
        raise SystemExit(0)

    reorient = do(
        Wait(1),
        Press('+'), Wait(1),
        Press('z'), Wait(.5), Press('L'), Wait(.5),
        Press('w', duration=2.5),
        # center camera
        Press('L'), Wait(.1),
    )

    states = {
        'INITIAL': (
            (
                match_px(Point(y=598, x=1160), Color(b=17, g=203, r=244)),
                do(Press('Y'), Wait(5), Press('$'), Wait(.5)),
                'REORIENT_INITIAL',
            ),
        ),
        'REORIENT_INITIAL': (
            (
                match_text(
                    'Map',
                    Point(y=90, x=226),
                    Point(y=124, x=276),
                    invert=False,
                ),
                do(Press('A'), Wait(1)),
                'REORIENT_INITIAL',
            ),
            (
                match_px(Point(y=598, x=1160), Color(b=17, g=203, r=244)),
                do(
                    reorient,
                    # open menu
                    Press('X'), Wait(1), Press('d'), Wait(1),
                ),
                'MENU',
            ),
        ),
        'MENU': (
            (
                match_px(Point(y=241, x=1161), Color(b=28, g=183, r=209)),
                do(
                    # press A on boxes menu
                    Wait(1), Press('A'), Wait(3),
                    # select first column
                    select,
                    # move it over
                    Press('a'), Wait(.4), Press('s'), Wait(.4),
                    Press('A'), Wait(.5),
                    # out to main menu
                    Press('B'), Wait(2),
                    Press('B'), Wait(1),
                ),
                'HATCH_5',
            ),
            (always_matches, do(Press('s'), Wait(.5)), 'MENU'),
        ),
        'HATCH_5': (
            (
                all_match(
                    match_px(Point(y=541, x=930), Color(b=49, g=43, r=30)),
                    match_text(
                        'Oh?',
                        Point(y=546, x=353),
                        Point(y=586, x=410),
                        invert=True,
                    ),
                ),
                do(Press('A'), Wait(15)),
                'HATCH_1',
            ),
            (eggs_done, Wait(3), 'NEXT_COLUMN'),
            (always_matches, do(start_left, Wait(1)), 'HATCH_5'),
        ),
        'HATCH_1': (
            (
                match_px(Point(y=598, x=1160), Color(b=17, g=203, r=244)),
                egg_hatched,
                'HATCH_5',
            ),
            (always_matches, do(Press('A'), Wait(1)), 'HATCH_1'),
        ),
        'NEXT_COLUMN': (
            (done, bye, 'INITIAL'),
            (
                always_matches,
                do(
                    # open menu, into boxes
                    Press('X'), Wait(2), Press('A'), Wait(3),
                    # select party to put it back
                    Press('a'), Wait(.5), Press('s'), Wait(.5),
                    select,
                    # position in first column of box
                    Press('d'), Wait(.5), Press('w'), Wait(.5),
                    # put the hatched ones back and pick up new column
                    move_to_column, Press('A'), Wait(.5),
                    pick_up_new_column,
                ),
                'TO_OVERWORLD',
            ),
        ),
        'TO_OVERWORLD': (
            (
                match_px(Point(y=598, x=1160), Color(b=17, g=203, r=244)),
                do(Press('Y'), Wait(5), Press('$'), Wait(.5)),
                'REORIENT_HATCH',
            ),
            (always_matches, do(Press('B'), Wait(1)), 'TO_OVERWORLD'),
        ),
        'REORIENT_HATCH': (
            (
                match_text(
                    'Map',
                    Point(y=90, x=226),
                    Point(y=124, x=276),
                    invert=False,
                ),
                do(Press('A'), Wait(1)),
                'REORIENT_HATCH',
            ),
            (
                match_px(Point(y=598, x=1160), Color(b=17, g=203, r=244)),
                reorient,
                'HATCH_5',
            ),
        ),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=vid, ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
