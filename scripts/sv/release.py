from __future__ import annotations

import argparse

import cv2
import serial

from scripts.engine import always_matches
from scripts.engine import bye
from scripts.engine import do
from scripts.engine import make_vid
from scripts.engine import Press
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import States
from scripts.engine import Wait
from scripts.sv._move_box import move_box
from scripts.sv._to_boxes import to_boxes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--boxes', type=int, required=True)
    args = parser.parse_args()

    box = 0

    def release_box(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        nonlocal box

        def _release() -> None:
            do(
                Press('A'), Wait(.75),
                Press('w'), Wait(.25),
                Press('w'), Wait(.25),
                Press('A'), Wait(1),
                Press('w'), Wait(.25),
                Press('A'), Wait(2),
                Press('A'), Wait(.75),
            )(vid, ser)

        for direction in 'dadad':
            _release()
            for _ in range(5):
                do(Press(direction), Wait(.25))(vid, ser)
                _release()
            do(Press('s'), Wait(.25))(vid, ser)

        for _ in range(2):
            do(Press('s'), Wait(.25))(vid, ser)
        for _ in range(5):
            do(Press('a'), Wait(.25))(vid, ser)

        box += 1

    def done(frame: object) -> bool:
        return box == args.boxes

    states: States = {
        **to_boxes('INITIAL', 'RELEASE_BOX'),
        'RELEASE_BOX': (
            (done, bye, 'INVALID'),
            (always_matches, release_box, 'NEXT_BOX'),
        ),
        **move_box('NEXT_BOX', 'RELEASE_BOX', 'R'),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=make_vid(), ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
