from __future__ import annotations

import argparse

import cv2
import serial

from scripts.engine import Action
from scripts.engine import always_matches
from scripts.engine import Color
from scripts.engine import do
from scripts.engine import match_px
from scripts.engine import Matcher
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import Wait


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--boxes', type=int, required=True)
    args = parser.parse_args()

    vid = cv2.VideoCapture(0)
    vid.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    vid.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    box = 0

    def release_box(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        nonlocal box

        def _release() -> None:
            do(
                Press('A'), Wait(.75),
                Press('w'), Wait(.75),
                Press('w'), Wait(.75),
                Press('A'), Wait(.75),
                Press('w'), Wait(.75),
                Press('A'), Wait(2),
                Press('A'), Wait(.75),
            )(vid, ser)

        for direction in 'dadad':
            _release()
            for _ in range(5):
                do(Press(direction), Wait(1))(vid, ser)
                _release()
            do(Press('s'), Wait(.75))(vid, ser)

        for _ in range(2):
            do(Press('s'), Wait(.75))(vid, ser)
        for _ in range(5):
            do(Press('a'), Wait(.75))(vid, ser)

        do(Press('R'), Wait(.75))(vid, ser)
        box += 1

    def done(frame: object) -> bool:
        return box == args.boxes

    def bye(vid: object, ser: object) -> None:
        raise SystemExit(0)

    states: dict[str, tuple[tuple[Matcher, Action, str], ...]]
    states = {
        'INITIAL': (
            (
                match_px(Point(y=399, x=696), Color(b=17, g=203, r=244)),
                do(Press('X'), Wait(1), Press('d'), Wait(1)),
                'MENU',
            ),
        ),
        'MENU': (
            (
                match_px(Point(y=161, x=697), Color(b=28, g=183, r=209)),
                # press A on boxes menu
                do(Wait(1), Press('A'), Wait(3)),
                'RELEASE_BOX',
            ),
            (always_matches, do(Press('s'), Wait(.75)), 'MENU'),
        ),
        'RELEASE_BOX': (
            (done, bye, 'INITIAL'),
            (always_matches, release_box, 'RESET_TIMEOUT'),
        ),
        'RESET_TIMEOUT': (
            (always_matches, Wait(1), 'RELEASE_BOX'),
        ),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=vid, ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
