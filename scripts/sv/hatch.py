from __future__ import annotations

import argparse

import cv2
import numpy
import serial

from scripts.engine import all_match
from scripts.engine import always_matches
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
from scripts.engine import States
from scripts.engine import Wait
from scripts.engine import Write
from scripts.sv._bootup import world
from scripts.sv._move_box import move_box
from scripts.sv._to_boxes import to_boxes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--boxes', type=int, required=True)
    args = parser.parse_args()

    require_tesseract()

    box = 0
    column = 0
    eggs = 5

    def eggs_done(frame: object) -> bool:
        return eggs == 0

    def egg_hatched(vid: object, ser: object) -> None:
        nonlocal eggs
        eggs -= 1

    def column_matches(frame: numpy.ndarray) -> bool:
        x = 372 + 84 * column
        return match_px(Point(y=169, x=x), Color(b=42, g=197, r=213))(frame)

    def multiselect_matches(frame: numpy.ndarray) -> bool:
        x = 300 + 84 * column
        return match_px(Point(y=133, x=x), Color(b=38, g=193, r=226))(frame)

    def column_done(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        nonlocal box, column, eggs
        eggs = 5
        if column == 5:
            column = 0
            box += 1
        else:
            column += 1

        print(f' box={box + 1} column={column + 1} '.center(79, '='))

    def all_done(frame: object) -> bool:
        return box == args.boxes

    def box_done(frame: object) -> bool:
        return column == 0

    pos0_matches = match_px(Point(y=169, x=372), Color(b=42, g=197, r=213))
    pos1_matches = match_px(Point(y=251, x=366), Color(b=47, g=189, r=220))
    party1_matches = match_px(Point(y=255, x=248), Color(b=22, g=198, r=229))
    sel_text_matches = match_text(
        'Draw Selection Box',
        Point(y=679, x=762),
        Point(y=703, x=909),
        invert=True,
    )

    states: States = {
        **to_boxes('INITIAL', 'PICKUP_TO_COLUMN'),
        # loop point
        'PICKUP_TO_COLUMN': (
            (column_matches, do(), 'PICKUP_MINUS'),
            (always_matches, do(Press('d'), Wait(.4)), 'PICKUP_TO_COLUMN'),
        ),
        'PICKUP_MINUS': (
            (sel_text_matches, do(Press('-'), Wait(.5)), 'PICKUP_MINUS'),
            (always_matches, Press('s', duration=1), 'PICKUP_SELECTION'),
        ),
        'PICKUP_SELECTION': (
            (multiselect_matches, do(Press('A'), Wait(1)), 'PICKUP_SELECTION'),
            (always_matches, do(), 'PICKUP_TO_0'),
        ),
        'PICKUP_TO_0': (
            (pos0_matches, do(), 'PICKUP_TO_1'),
            (always_matches, do(Press('a'), Wait(.5)), 'PICKUP_TO_0'),
        ),
        'PICKUP_TO_1': (
            (pos1_matches, do(), 'PICKUP_TO_PARTY'),
            (always_matches, do(Press('s'), Wait(.5)), 'PICKUP_TO_1'),
        ),
        'PICKUP_TO_PARTY': (
            (party1_matches, do(), 'PICKUP_DROP'),
            (always_matches, do(Press('a'), Wait(.5)), 'PICKUP_TO_PARTY'),
        ),
        'PICKUP_DROP': (
            (sel_text_matches, do(), 'PICKUP_EXIT_BOX'),
            (always_matches, do(Press('A'), Wait(1)), 'PICKUP_DROP'),
        ),
        'PICKUP_EXIT_BOX': (
            (world, do(), 'REORIENT_OPEN_MAP'),
            (always_matches, do(Press('B'), Wait(1)), 'PICKUP_EXIT_BOX'),
        ),
        'REORIENT_OPEN_MAP': (
            (world, do(Press('Y'), Wait(5)), 'REORIENT_OPEN_MAP'),
            (always_matches, do(), 'REORIENT_FIND_ZERO'),
        ),
        'REORIENT_FIND_ZERO': (
            (
                match_text(
                    'Zero Gate',
                    Point(y=251, x=584),
                    Point(y=280, x=695),
                    invert=False,
                ),
                do(),
                'REORIENT_MASH_A',
            ),
            (
                always_matches,
                do(Press('$', duration=.11), Wait(1)),
                'REORIENT_FIND_ZERO',
            ),
        ),
        'REORIENT_MASH_A': (
            (
                match_text(
                    'Map',
                    Point(y=90, x=226),
                    Point(y=124, x=276),
                    invert=False,
                ),
                do(Press('A'), Wait(1)),
                'REORIENT_MASH_A',
            ),
            (always_matches, do(), 'REORIENT_MOVE'),
        ),
        'REORIENT_MOVE': (
            (
                world,
                do(
                    Wait(1),
                    Press('+'), Wait(1),
                    Press('z'), Wait(.5), Press('L'), Wait(.5),
                    Press('w', duration=2.5),
                    Press('L'), Wait(.1),
                ),
                'HATCH_5',
            ),
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
            (eggs_done, Wait(3), 'DEPOSIT_MENU'),
            (always_matches, do(Write('#'), Wait(1)), 'HATCH_5'),
        ),
        'HATCH_1': (
            (
                match_px(Point(y=598, x=1160), Color(b=17, g=203, r=244)),
                egg_hatched,
                'HATCH_5',
            ),
            (always_matches, do(Press('A'), Wait(1)), 'HATCH_1'),
        ),
        **to_boxes('DEPOSIT_MENU', 'DEPOSIT_TO_1'),
        'DEPOSIT_TO_1': (
            (pos1_matches, do(), 'DEPOSIT_TO_PARTY'),
            (always_matches, do(Press('s'), Wait(.5)), 'DEPOSIT_TO_1'),
        ),
        'DEPOSIT_TO_PARTY': (
            (party1_matches, do(), 'DEPOSIT_MINUS'),
            (always_matches, do(Press('a'), Wait(.5)), 'DEPOSIT_TO_PARTY'),
        ),
        'DEPOSIT_MINUS': (
            (sel_text_matches, do(Press('-'), Wait(.5)), 'DEPOSIT_MINUS'),
            (always_matches, Press('s', duration=1), 'DEPOSIT_SELECTION'),
        ),
        'DEPOSIT_SELECTION': (
            (
                match_px(Point(y=217, x=27), Color(b=15, g=200, r=234)),
                do(Press('A'), Wait(1)),
                'DEPOSIT_SELECTION',
            ),
            (always_matches, do(), 'DEPOSIT_BACK_TO_1'),
        ),
        'DEPOSIT_BACK_TO_1': (
            (pos1_matches, do(), 'DEPOSIT_BACK_TO_0'),
            (always_matches, do(Press('d'), Wait(.5)), 'DEPOSIT_BACK_TO_1'),
        ),
        'DEPOSIT_BACK_TO_0': (
            (pos0_matches, do(), 'DEPOSIT_TO_COLUMN'),
            (always_matches, do(Press('w'), Wait(.5)), 'DEPOSIT_BACK_TO_0'),
        ),
        'DEPOSIT_TO_COLUMN': (
            (column_matches, do(), 'DEPOSIT_DROP'),
            (always_matches, do(Press('d'), Wait(.5)), 'DEPOSIT_TO_COLUMN'),
        ),
        'DEPOSIT_DROP': (
            (sel_text_matches, column_done, 'DEPOSIT_NEXT'),
            (always_matches, do(Press('A'), Wait(1)), 'DEPOSIT_DROP'),
        ),
        'DEPOSIT_NEXT': (
            (all_done, bye, 'INVALID'),
            (box_done, do(), 'DEPOSIT_NEXT_BOX'),
            (always_matches, do(), 'PICKUP_TO_COLUMN'),
        ),
        **move_box('DEPOSIT_NEXT_BOX', 'PICKUP_TO_COLUMN', 'R'),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=make_vid(), ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
