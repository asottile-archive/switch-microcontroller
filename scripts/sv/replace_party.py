from __future__ import annotations

import argparse

import serial

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
from scripts.sv._bootup import world
from scripts.sv._move_box import move_box
from scripts.sv._to_boxes import to_boxes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    args = parser.parse_args()

    require_tesseract()

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
        **to_boxes('INITIAL', 'BOX_LEFT'),
        **move_box('BOX_LEFT', 'PARTY_TOP', 'L'),
        'PARTY_TOP': (
            (
                match_px(Point(y=152, x=248), Color(b=22, g=198, r=229)),
                do(),
                'PICK_UP_PARTY_TOP',
            ),
            (always_matches, do(Press('a'), Wait(.5)), 'PARTY_TOP'),
        ),
        'PICK_UP_PARTY_TOP': (
            (sel_text_matches, do(Press('Y'), Wait(.5)), 'PICK_UP_PARTY_TOP'),
            (always_matches, do(), 'TO_SPOT_2'),
        ),
        'TO_SPOT_2': (
            (
                match_px(Point(y=156, x=453), Color(b=38, g=199, r=207)),
                do(),
                'DROP_PARTY_TOP',
            ),
            (always_matches, do(Press('d'), Wait(.5)), 'TO_SPOT_2'),
        ),
        'DROP_PARTY_TOP': (
            (sel_text_matches, do(), 'TO_0'),
            (always_matches, do(Press('A'), Wait(1)), 'DROP_PARTY_TOP'),
        ),
        'TO_0': (
            (pos0_matches, do(), 'TO_1'),
            (always_matches, do(Press('a'), Wait(.5)), 'TO_0'),
        ),
        'TO_1': (
            (pos1_matches, do(), 'TO_PARTY'),
            (always_matches, do(Press('s'), Wait(.5)), 'TO_1'),
        ),
        'TO_PARTY': (
            (party1_matches, do(), 'PARTY_MINUS'),
            (always_matches, do(Press('a'), Wait(.5)), 'TO_PARTY'),
        ),
        'PARTY_MINUS': (
            (sel_text_matches, do(Press('-'), Wait(.5)), 'PARTY_MINUS'),
            (always_matches, Press('s', duration=1), 'PARTY_SELECTION'),
        ),
        'PARTY_SELECTION': (
            (
                match_px(Point(y=217, x=27), Color(b=15, g=200, r=234)),
                do(Press('A'), Wait(1)),
                'PARTY_SELECTION',
            ),
            (always_matches, do(), 'FROM_1'),
        ),
        'FROM_1': (
            (pos1_matches, do(), 'FROM_0'),
            (always_matches, do(Press('d'), Wait(.5)), 'FROM_1'),
        ),
        'FROM_0': (
            (pos0_matches, do(), 'DROP'),
            (always_matches, do(Press('w'), Wait(.5)), 'FROM_0'),
        ),
        'DROP': (
            (sel_text_matches, do(), 'BOX_RIGHT'),
            (always_matches, do(Press('A'), Wait(.5)), 'DROP'),
        ),
        **move_box('BOX_RIGHT', 'OUT', 'R'),
        'OUT': (
            (world, bye, 'INVALID'),
            (always_matches, do(Press('B'), Wait(.5)), 'OUT'),
        ),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=make_vid(), ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
